/**
 * Planner Store — live execution plan state during SSE streaming
 * Documented Requirement: SSE tool_status events → ToolCard states (§5.2, §12)
 * Drives the Live Execution Plan Visualizer screen.
 */

import { create } from 'zustand'
import type { ExecutionPlan, QuerySpec, ToolCardModel, ToolState } from '@/types'
import { TOOL_LABELS } from '@/constants'

interface PlannerState {
  // Parsed intent from SSE intent_parsed (§12)
  querySpec: QuerySpec | null
  setQuerySpec: (spec: QuerySpec) => void

  // Streaming reasoning text for typewriter ticker (§5.2)
  reasoningText: string
  appendReasoning: (text: string) => void
  setReasoningComplete: (text: string) => void

  // Tool cards — dynamically assembled as SSE events arrive (§5.2)
  toolCards: ToolCardModel[]
  upsertToolCard: (tool: string, state: ToolState, progress?: number, skipReason?: string) => void

  // Final plan (received on plan_complete)
  executionPlan: ExecutionPlan | null
  setExecutionPlan: (plan: ExecutionPlan) => void

  // Planning indicator — true while agent is actively planning (§7.3 breathing pulse)
  isPlanning: boolean
  setIsPlanning: (planning: boolean) => void

  reset: () => void
}

export const usePlannerStore = create<PlannerState>((set) => ({
  querySpec: null,
  setQuerySpec: (spec) => set({ querySpec: spec }),

  reasoningText: '',
  appendReasoning: (text) =>
    set((s) => ({ reasoningText: s.reasoningText + text })),
  setReasoningComplete: (text) => set({ reasoningText: text }),

  toolCards: [],
  upsertToolCard: (tool, state, progress = 0, skipReason) =>
    set((s) => {
      const existing = s.toolCards.findIndex((c) => c.name === tool)
      const card: ToolCardModel = {
        name:  tool,
        label: TOOL_LABELS[tool] ?? tool.toUpperCase(),
        state,
        progress,
        skipReason,
      }
      if (existing === -1) {
        return { toolCards: [...s.toolCards, card] }
      }
      const updated = [...s.toolCards]
      updated[existing] = card
      return { toolCards: updated }
    }),

  executionPlan: null,
  setExecutionPlan: (plan) => set({ executionPlan: plan }),

  isPlanning: false,
  setIsPlanning: (planning) => set({ isPlanning: planning }),

  reset: () =>
    set({
      querySpec: null,
      reasoningText: '',
      toolCards: [],
      executionPlan: null,
      isPlanning: false,
    }),
}))
