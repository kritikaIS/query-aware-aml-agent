/**
 * useQuery — orchestrates query submission against the real backend.
 * Documented Requirement: §12 data flow — POST /query → stores → UI
 *
 * Bug fix: getPlannerQuerySpec and getPlannerExecPlan were Zustand state
 * subscriptions included in useCallback's deps array. When synthetic SSE
 * events fired and updated plannerStore, those values changed, causing
 * submitQuery to be recreated. QueryConsole re-rendered, which reset
 * cleanupRef and cleared all scheduled timers — so report_ready never fired
 * and the view never transitioned to 'results'.
 *
 * Fix: track whether querySpec / executionPlan were already set during this
 * event sequence using a plain local ref (no Zustand subscription needed).
 * The useCallback dep array no longer includes any reactive Zustand values,
 * so submitQuery is stable across the full lifecycle of a single query.
 */

import { useCallback, useRef } from 'react'
import {
  useQueryStore,
  usePlannerStore,
  useReportStore,
  useUiStore,
} from '@/stores'
import { connectSse, pollQuery } from '@/services/api'
import { MOCK_EXECUTION_REPORT } from '@/features/results/mock'
import { MOCK_QUERY_SPEC, MOCK_EXECUTION_PLAN } from '@/features/plan/mock'
import type { SseEvent } from '@/types'

const MAX_RETRIES = 2

export function useQuery() {
  // Select stable action functions — these never change identity in Zustand
  const resetQuery        = useQueryStore((s) => s.reset)
  const setSubmittedQuery = useQueryStore((s) => s.setSubmittedQuery)
  const setQueryStatus    = useQueryStore((s) => s.setStatus)
  const setQueryError     = useQueryStore((s) => s.setError)

  const resetPlanner         = usePlannerStore((s) => s.reset)
  const setIsPlanning        = usePlannerStore((s) => s.setIsPlanning)
  const setQuerySpec         = usePlannerStore((s) => s.setQuerySpec)
  const upsertToolCard       = usePlannerStore((s) => s.upsertToolCard)
  const setExecutionPlan     = usePlannerStore((s) => s.setExecutionPlan)
  const setReasoningComplete = usePlannerStore((s) => s.setReasoningComplete)

  const resetReport = useReportStore((s) => s.reset)
  const setReport   = useReportStore((s) => s.setReport)

  const setView          = useUiStore((s) => s.setView)
  const setSkipToResults = useUiStore((s) => s.setSkipToResults)
  const addToast         = useUiStore((s) => s.addToast)

  const cleanupRef = useRef<(() => void) | null>(null)
  const retriesRef = useRef(0)

  const submitQuery = useCallback((query: string) => {
    cleanupRef.current?.()
    retriesRef.current = 0

    resetQuery()
    resetPlanner()
    resetReport()
    setSkipToResults(false)

    setSubmittedQuery(query)
    setQueryStatus('submitting')
    setIsPlanning(true)
    setView('plan')

    // Track what has been set during this event sequence locally —
    // NOT via Zustand subscriptions (which would change useCallback deps
    // and recreate submitQuery mid-flight, clearing the timer chain).
    let querySpecSet     = false
    let executionPlanSet = false

    const handleEvent = (event: SseEvent) => {
      switch (event.type) {
        case 'intent_parsed':
          setQueryStatus('streaming')
          setQuerySpec(event.query_spec)
          querySpecSet = true
          break

        case 'tool_status':
          upsertToolCard(event.tool, event.state, event.progress, event.reason)
          break

        case 'plan_complete':
          setExecutionPlan(event.execution_plan)
          setReasoningComplete(event.execution_plan.reasoning)
          setIsPlanning(false)
          executionPlanSet = true
          break

        case 'report_ready':
          setReport(event.report)
          setQueryStatus('complete')
          setIsPlanning(false)
          // Back-fill querySpec / executionPlan if not already set by earlier events
          if (!querySpecSet) {
            setQuerySpec(event.report.query_spec)
          }
          if (!executionPlanSet) {
            setExecutionPlan(event.report.execution_plan)
            setReasoningComplete(event.report.execution_plan.reasoning)
          }
          // Transition to Results Dashboard
          setView('results')
          break

        case 'error':
          setQueryStatus('error')
          setQueryError(event.message)
          setIsPlanning(false)
          addToast({ type: 'error', message: event.message })
          break
      }
    }

    const handleFallbackToMock = (reason: string) => {
      console.warn('[Backend] Falling back to mock data:', reason)
      setQuerySpec(MOCK_QUERY_SPEC)
      setExecutionPlan(MOCK_EXECUTION_PLAN)
      setReasoningComplete(MOCK_EXECUTION_PLAN.reasoning)
      setIsPlanning(false)
      setReport(MOCK_EXECUTION_REPORT)
      setQueryStatus('complete')
      setView('results')
      addToast({
        type: 'warning',
        message: `Backend unavailable — showing demo data. (${reason})`,
      })
    }

    const handleError = (err: Event | Error) => {
      const message = err instanceof Error ? err.message : 'Connection error'
      console.warn('[API] Primary request failed:', message)
      if (retriesRef.current < MAX_RETRIES) {
        retriesRef.current++
        console.info(`[API] Retry ${retriesRef.current}/${MAX_RETRIES}`)
        cleanupRef.current = pollQuery(query, { onEvent: handleEvent, onError: handleRestError })
      } else {
        handleFallbackToMock(message)
      }
    }

    const handleRestError = (err: Event | Error) => {
      const message = err instanceof Error ? err.message : 'Request failed'
      console.warn('[API] Poll fallback failed:', message)
      handleFallbackToMock(message)
    }

    cleanupRef.current = connectSse(query, { onEvent: handleEvent, onError: handleError })
  }, [
    // Only stable Zustand action functions — none of these ever change identity,
    // so submitQuery is created once and stays stable for the component's lifetime.
    resetQuery, resetPlanner, resetReport, setSkipToResults,
    setSubmittedQuery, setQueryStatus, setIsPlanning, setView,
    setQuerySpec, upsertToolCard, setExecutionPlan, setReasoningComplete,
    setReport, setQueryError, addToast,
  ])

  const cancelQuery = useCallback(() => {
    cleanupRef.current?.()
    cleanupRef.current = null
  }, [])

  return { submitQuery, cancelQuery }
}
