/**
 * useMockPlanDriver — replays the mock SSE event sequence into Zustand stores.
 * Documented Requirement: §12 data flow — SSE events drive plannerStore.
 * For this screen: no backend, no SSE. Mock driver replays MOCK_TOOL_EVENTS
 * via timers, exactly as the real SSE handler would.
 *
 * Drives:
 *   plannerStore.setQuerySpec()
 *   plannerStore.setIsPlanning()
 *   plannerStore.upsertToolCard()
 *   plannerStore.setReasoningComplete()
 *   plannerStore.setExecutionPlan()
 *   queryStore.setSubmittedQuery()
 */

import { useEffect, useRef } from 'react'
import { usePlannerStore, useQueryStore } from '@/stores'
import {
  MOCK_QUERY,
  MOCK_QUERY_SPEC,
  MOCK_EXECUTION_PLAN,
  MOCK_TOOL_EVENTS,
} from './mock'

export function useMockPlanDriver() {
  const plannerStore = usePlannerStore()
  const queryStore   = useQueryStore()
  const timersRef    = useRef<ReturnType<typeof setTimeout>[]>([])

  useEffect(() => {
    // Reset stores before driving
    plannerStore.reset()
    queryStore.reset()

    // Set the submitted query (shown in the header)
    queryStore.setSubmittedQuery(MOCK_QUERY)
    queryStore.setStatus('streaming')

    // Step 0 — intent parsed (immediate)
    plannerStore.setQuerySpec(MOCK_QUERY_SPEC)
    plannerStore.setIsPlanning(true)

    // Accumulate cumulative delay so events replay in order
    let cumulativeDelay = 0

    MOCK_TOOL_EVENTS.forEach((event) => {
      cumulativeDelay += event.delay
      const id = setTimeout(() => {
        plannerStore.upsertToolCard(
          event.tool,
          event.state,
          event.progress,
          event.skipReason
        )
      }, cumulativeDelay)
      timersRef.current.push(id)
    })

    // plan_complete: fire after all tool events + a small buffer
    const planCompleteDelay = cumulativeDelay + 200
    const planId = setTimeout(() => {
      plannerStore.setExecutionPlan(MOCK_EXECUTION_PLAN)
      plannerStore.setReasoningComplete(MOCK_EXECUTION_PLAN.reasoning)
      plannerStore.setIsPlanning(false)
      queryStore.setStatus('complete')
    }, planCompleteDelay)
    timersRef.current.push(planId)

    // Cleanup: clear all timers on unmount
    return () => {
      timersRef.current.forEach(clearTimeout)
      timersRef.current = []
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Mount-only — one replay per screen mount
}
