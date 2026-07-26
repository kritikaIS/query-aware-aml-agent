/**
 * Query execution service
 * Backend contract: POST /query is synchronous — no SSE endpoint exists.
 * Frontend Design §11: "falls back to polling if SSE blocked on the demo network"
 * Since the backend is synchronous, the "SSE" path is emulated:
 *   1. POST /query → wait for full ExecutionReport
 *   2. Synthesise the SSE event sequence from the response
 *   3. Fire events so the Plan Visualizer animation plays correctly
 *
 * This preserves all UI animations while using the real backend.
 */

import { postQuery, ApiError } from './client'
import type { SseEvent, ExecutionReport } from '@/types'

export interface SseCallbacks {
  onEvent: (event: SseEvent) => void
  onError: (error: Event | Error) => void
  onOpen?:  () => void
}

/**
 * Execute a query against the real backend.
 * Fires synthesised SSE events so the Plan Visualizer renders correctly.
 * Returns a cleanup no-op (request cannot be cancelled mid-flight with fetch).
 *
 * Event sequence emitted:
 *   intent_parsed  → from response.query_spec
 *   tool_status(running) × N  → one per execution_plan.step
 *   tool_status(skipped) × M  → one per skipped_tool
 *   plan_complete  → from response.execution_plan
 *   report_ready   → the full report
 *
 * Timing: events are fired with small synthetic delays so animations play.
 * All delays are bounded within the 3s plan animation budget (§13).
 */
export function connectSse(query: string, callbacks: SseCallbacks): () => void {
  let cancelled = false
  const timers: ReturnType<typeof setTimeout>[] = []

  const schedule = (fn: () => void, delayMs: number) => {
    const id = setTimeout(() => { if (!cancelled) fn() }, delayMs)
    timers.push(id)
  }

  callbacks.onOpen?.()

  const run = async () => {
    try {
      // Real backend call — synchronous, may take several seconds
      const report = await postQuery({ query })
      if (cancelled) return

      // Synthesise the SSE event sequence from the completed report
      emitSyntheticEvents(report, callbacks, schedule)

    } catch (err) {
      if (cancelled) return
      const error = err instanceof Error ? err : new Error(String(err))
      callbacks.onError(error)
    }
  }

  run()

  return () => {
    cancelled = true
    timers.forEach(clearTimeout)
  }
}

/**
 * Fires synthesised SSE events derived from a completed ExecutionReport.
 * Delays are staggered so the Plan Visualizer animations play naturally.
 */
function emitSyntheticEvents(
  report: ExecutionReport,
  callbacks: SseCallbacks,
  schedule: (fn: () => void, ms: number) => void
): void {
  let t = 0
  const STEP   = 120   // ms between synthetic tool events
  const GAP    = 60    // ms before transitions

  // 1. intent_parsed — immediate
  callbacks.onEvent({ type: 'intent_parsed', query_spec: report.query_spec })
  t += GAP

  const { steps, skipped_tools } = report.execution_plan

  // 2. tool_status events — one per step (running → done)
  steps.forEach((step) => {
    const toolName = step.tool
    // running
    schedule(() => callbacks.onEvent({
      type: 'tool_status', tool: toolName, state: 'running', progress: 50,
    }), t)
    t += STEP
    // done
    schedule(() => callbacks.onEvent({
      type: 'tool_status', tool: toolName, state: 'done', progress: 100,
    }), t)
    t += STEP
  })

  // 3. skipped tool events — appear after active tools
  skipped_tools.forEach((skipped) => {
    schedule(() => callbacks.onEvent({
      type: 'tool_status',
      tool:  skipped.tool,
      state: 'skipped',
      progress: 0,
      reason: skipped.reason,
    }), t)
    t += GAP
  })

  // 4. plan_complete
  schedule(() => callbacks.onEvent({
    type: 'plan_complete',
    execution_plan: report.execution_plan,
  }), t)
  t += GAP

  // 5. report_ready — triggers Results Dashboard
  schedule(() => callbacks.onEvent({
    type: 'report_ready',
    report,
  }), t)
}

/**
 * Direct REST fallback — used when connectSse itself throws before firing any events.
 * Calls POST /query and fires a single report_ready event.
 */
export function pollQuery(
  query: string,
  callbacks: SseCallbacks,
  _intervalMs = 500   // kept for interface compat, not used with sync backend
): () => void {
  let stopped = false

  const run = async () => {
    try {
      const report = await postQuery({ query })
      if (!stopped) {
        callbacks.onEvent({ type: 'report_ready', report })
      }
    } catch (err) {
      if (!stopped) {
        const message = err instanceof ApiError
          ? err.userMessage
          : (err instanceof Error ? err.message : 'Request failed')
        callbacks.onError(new Error(message))
      }
    }
  }

  run()

  return () => { stopped = true }
}
