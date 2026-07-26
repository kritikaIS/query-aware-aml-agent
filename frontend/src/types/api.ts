/**
 * API Types — mirrors the Python Pydantic schemas exactly.
 * Documented Requirement: ExecutionReport schema (Solution Design §8)
 * Frontend never computes a number — all values read from this payload (§12)
 */

// ── QuerySpec (Solution Design §4.1) ──────────────────────────────────
export type QueryIntent =
  | 'pattern_detection'
  | 'aggregation_rule'
  | 'entity_lookup'
  | 'broad_exploration'

export type AmlPattern =
  | 'structuring'
  | 'smurfing'
  | 'layering'
  | 'rapid_cashout'
  | null

export interface Filters {
  date_range: { start: string; end: string } | null
  customer_id: string | null
  segment: string | null
  country: string | null
  transaction_type: string | null
}

export interface ExplicitRule {
  condition: string | null
  present: boolean
}

export interface QuerySpec {
  intent: QueryIntent
  aml_pattern: AmlPattern
  filters: Filters
  explicit_rule: ExplicitRule
  requires_ml_anomaly_detection: boolean
  requires_full_eda: boolean
}

// ── ExecutionPlan (Solution Design §4.2) ──────────────────────────────
export interface PlanStep {
  tool: string
  args: Record<string, unknown>
}

export interface SkippedTool {
  tool: string
  reason: string
}

export interface ExecutionPlan {
  plan_id: string
  reasoning: string
  steps: PlanStep[]
  skipped_tools: SkippedTool[]
}

// ── ExecutionReport (Solution Design §8) ──────────────────────────────
export interface ContributingFeature {
  feature: string
  value: number
  z_score: number
}

export type RiskBand = 'Low' | 'Medium' | 'High'

export interface FlaggedEntity {
  customer_id: string
  risk_score: number
  risk_band: RiskBand
  aml_pattern_matched: AmlPattern
  top_contributing_features: ContributingFeature[]
  explanation: string
  recommended_action: string
}

export interface SummaryMetrics {
  total_transactions_scanned: number
  entities_flagged: number
  high_risk: number
  medium_risk: number
  low_risk: number
}

export interface ExecutionReport {
  user_query: string
  query_spec: QuerySpec
  execution_plan: ExecutionPlan
  flagged_entities: FlaggedEntity[]
  summary_metrics: SummaryMetrics
  charts: string[]
  _meta?: {
    elapsed_ms: number
    plan_id: string
    tools_invoked: string[]
    tools_skipped: Array<{ tool: string; reason: string }>
  }
}

// ── Request ────────────────────────────────────────────────────────────
export interface QueryRequest {
  query: string
}

// ── SSE Event shapes (§12 data flow, §11 SSE) ─────────────────────────
export type SseEventType =
  | 'intent_parsed'
  | 'tool_status'
  | 'plan_complete'
  | 'report_ready'
  | 'error'

export type ToolState = 'queued' | 'running' | 'done' | 'skipped' | 'error'

export interface SseIntentParsed {
  type: 'intent_parsed'
  query_spec: QuerySpec
}

export interface SseToolStatus {
  type: 'tool_status'
  tool: string
  state: ToolState
  progress?: number    // 0–100
  reason?: string      // populated for 'skipped' state
}

export interface SsePlanComplete {
  type: 'plan_complete'
  execution_plan: ExecutionPlan
}

export interface SseReportReady {
  type: 'report_ready'
  report: ExecutionReport
}

export interface SseError {
  type: 'error'
  message: string
}

export type SseEvent =
  | SseIntentParsed
  | SseToolStatus
  | SsePlanComplete
  | SseReportReady
  | SseError
