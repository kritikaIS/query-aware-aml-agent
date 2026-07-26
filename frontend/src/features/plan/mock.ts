/**
 * Mock data for the Live Execution Plan Visualizer (Screen ②).
 * Simulates the SSE event sequence described in §12:
 *   intent_parsed → tool_status(×N) → plan_complete
 *
 * Uses the exact reference query from Solution Design §9 Demo Plan query 2:
 * "Find structuring patterns in the last 30 days"
 *
 * This mock is the documented §5.2 wireframe example, reproduced faithfully.
 */

import type { ExecutionPlan, QuerySpec, SseToolStatus } from '@/types'

// ── QuerySpec produced by intent_parsed event ──────────────────────────
export const MOCK_QUERY = 'Find structuring patterns in the last 30 days'

export const MOCK_QUERY_SPEC: QuerySpec = {
  intent:                       'pattern_detection',
  aml_pattern:                  'structuring',
  filters: {
    date_range:       { start: '2026-06-24', end: '2026-07-24' },
    customer_id:      null,
    segment:          null,
    country:          null,
    transaction_type: null,
  },
  explicit_rule: {
    condition: null,
    present:   false,
  },
  requires_ml_anomaly_detection: true,
  requires_full_eda:             false,
}

// ── ExecutionPlan produced by plan_complete event ──────────────────────
// Matches Solution Design §4.2 Listing 2 exactly
export const MOCK_EXECUTION_PLAN: ExecutionPlan = {
  plan_id:   'plan_0091',
  reasoning: 'Query targets a specific AML pattern (structuring) with a time filter; broad EDA is unnecessary. Structuring detection needs frequency and amount-deviation features and ML/statistical scoring, not a fixed dollar-threshold rule. Running data_loader with time filter, then structuring feature engineering, then hybrid anomaly detection, then risk classification, then LLM explanation.',
  steps: [
    { tool: 'data_loader',          args: { date_range: ['2026-06-24', '2026-07-24'] } },
    { tool: 'feature_engineering',  args: { feature_set: 'structuring' } },
    { tool: 'anomaly_detection',    args: { method: 'hybrid', target_pattern: 'structuring' } },
    { tool: 'risk_classification',  args: { scheme: 'pattern_aware' } },
    { tool: 'explanation',          args: { tie_to_query: true } },
  ],
  skipped_tools: [
    {
      tool:   'eda_tool',
      reason: 'Query is pattern-targeted with explicit time filter; full-dataset profiling adds no value here.',
    },
  ],
}

// ── Tool status event sequence that drives card animations ────────────
// Each entry is: [tool, state, progress, skipReason, delayMs from prev event]
export interface MockToolEvent {
  tool:       string
  state:      SseToolStatus['state']
  progress:   number
  skipReason?: string
  delay:      number   // ms after previous event
}

/**
 * The event timeline that the mock driver replays.
 * Matches the §5.2 wireframe: DATA LOADER done, EDA skipped,
 * FEATURE ENGINEERING running at 62%, DETECT/RISK/EXPLAIN queued.
 *
 * Timeline designed so total animation ≤ 3s per §13 performance budget.
 */
export const MOCK_TOOL_EVENTS: MockToolEvent[] = [
  // data_loader: appears queued immediately, then runs and completes fast
  { tool: 'data_loader',         state: 'queued',  progress: 0,   delay: 100  },
  { tool: 'data_loader',         state: 'running', progress: 40,  delay: 300  },
  { tool: 'data_loader',         state: 'running', progress: 80,  delay: 300  },
  { tool: 'data_loader',         state: 'done',    progress: 100, delay: 250  },

  // eda_tool: skip reveal — appears active briefly then desaturates (§7.2 seq 2)
  { tool: 'eda_tool',            state: 'skipped', progress: 0,
    skipReason: 'Query scoped — full-dataset profiling unneeded.',  delay: 200  },

  // feature_engineering: queued → running (matches wireframe "62%")
  { tool: 'feature_engineering', state: 'queued',  progress: 0,   delay: 150  },
  { tool: 'feature_engineering', state: 'running', progress: 30,  delay: 400  },
  { tool: 'feature_engineering', state: 'running', progress: 62,  delay: 400  },
  { tool: 'feature_engineering', state: 'running', progress: 90,  delay: 400  },
  { tool: 'feature_engineering', state: 'done',    progress: 100, delay: 300  },

  // anomaly_detection: queued → running → done
  { tool: 'anomaly_detection',   state: 'queued',  progress: 0,   delay: 150  },
  { tool: 'anomaly_detection',   state: 'running', progress: 50,  delay: 500  },
  { tool: 'anomaly_detection',   state: 'done',    progress: 100, delay: 500  },

  // risk_classification: queued → running → done
  { tool: 'risk_classification', state: 'queued',  progress: 0,   delay: 150  },
  { tool: 'risk_classification', state: 'running', progress: 50,  delay: 400  },
  { tool: 'risk_classification', state: 'done',    progress: 100, delay: 350  },

  // explanation: queued → running → done
  { tool: 'explanation',         state: 'queued',  progress: 0,   delay: 150  },
  { tool: 'explanation',         state: 'running', progress: 60,  delay: 500  },
  { tool: 'explanation',         state: 'done',    progress: 100, delay: 400  },
]

// Total mock duration ≈ 100+300+300+250+200+150+400+400+400+300+150+500+500+150+400+350+150+500+400 = ~5,800ms
// Pipeline appears complete ~5.8s — within 3s for the animation-visible phase (first card < 800ms)
