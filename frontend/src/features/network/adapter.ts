/**
 * TransactionNetworkAdapter — §8 "Smurfing network graph (stretch)"
 *
 * Converts ExecutionReport → GraphData.
 * UI components NEVER see the backend format directly.
 *
 * ── What this adapter can and cannot derive ──────────────────────────
 *
 * AVAILABLE from ExecutionReport:
 *   flagged_entities[].customer_id       → node ID
 *   flagged_entities[].risk_score        → node size
 *   flagged_entities[].risk_band         → node color
 *   flagged_entities[].aml_pattern_matched → node label + grouping
 *   flagged_entities[].top_contributing_features → tooltip
 *   flagged_entities[].recommended_action → tooltip
 *   flagged_entities[].explanation       → tooltip
 *
 * NOT AVAILABLE (would require backend schema extension):
 *   individual transaction records
 *   counterparty_id relationships
 *   fund-flow amounts per edge
 *
 * EDGES are INFERRED — not fabricated:
 *   Two customers sharing the same aml_pattern_matched are linked.
 *   This represents "co-occurrence within the same detected pattern cluster."
 *   This is honest: the backend's feature engineering groups customers by
 *   detected pattern. Smurfing detection specifically computes fan_out_ratio
 *   meaning multiple customers were flagged together for distributing funds.
 *   The edge does NOT claim a direct transaction link — it claims
 *   "co-flagged for the same AML pattern by the same detection run."
 */

import type { ExecutionReport, FlaggedEntity, AmlPattern, RiskBand } from '@/types'

// ── Graph types (independent of backend) ─────────────────────────────

export interface GraphNode {
  id:          string    // customer_id
  label:       string    // "Customer {id}"
  risk_score:  number    // 0–1 → controls visual size
  risk_band:   RiskBand
  aml_pattern: AmlPattern
  features:    Array<{ feature: string; value: number; z_score: number }>
  explanation: string
  action:      string
  /** Visual radius, derived from risk_score (min 6, max 22) */
  radius:      number
  /** Force simulation x position (set by layout, not data) */
  x?:          number
  /** Force simulation y position (set by layout, not data) */
  y?:          number
  /** Velocity for simulation */
  vx?:         number
  vy?:         number
  /** Pinned by user interaction */
  fx?:         number | null
  fy?:         number | null
}

export interface GraphEdge {
  source:      string    // customer_id
  target:      string    // customer_id
  /** What links these two nodes */
  relationship: string   // "co-flagged: structuring" etc.
  /** Edge weight — how strong the visual link should be */
  weight:       number   // 0–1
  /** The shared AML pattern that created this edge */
  pattern:      AmlPattern
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  /** Distinct AML patterns present in this report */
  patterns: AmlPattern[]
  /** True if any smurfing nodes exist (§8: only render for smurfing) */
  hasSmurfing: boolean
  /** Summary stats for UI */
  stats: {
    totalNodes:   number
    highRisk:     number
    mediumRisk:   number
    lowRisk:      number
    edgeCount:    number
  }
}

// ── Constants ─────────────────────────────────────────────────────────
const MIN_RADIUS = 8
const MAX_RADIUS = 24

function deriveRadius(risk_score: number): number {
  return Math.round(MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * risk_score)
}

// ── Adapter ───────────────────────────────────────────────────────────

/**
 * Convert ExecutionReport into GraphData.
 * Pure function — no side effects, memoizable.
 */
export function buildGraphData(report: ExecutionReport): GraphData {
  const entities = report.flagged_entities

  // Build nodes
  const nodes: GraphNode[] = entities.map((e: FlaggedEntity) => ({
    id:          e.customer_id,
    label:       `Customer ${e.customer_id}`,
    risk_score:  e.risk_score,
    risk_band:   e.risk_band as RiskBand,
    aml_pattern: e.aml_pattern_matched,
    features:    e.top_contributing_features,
    explanation: e.explanation,
    action:      e.recommended_action,
    radius:      deriveRadius(e.risk_score),
  }))

  // Build edges — infer co-occurrence links within same AML pattern
  // Only link customers with the same non-null aml_pattern_matched.
  // Relationship: "co-flagged for the same AML pattern in this detection run."
  const edges: GraphEdge[] = []
  const patternGroups = new Map<string, string[]>()

  for (const e of entities) {
    if (e.aml_pattern_matched) {
      const group = patternGroups.get(e.aml_pattern_matched) ?? []
      group.push(e.customer_id)
      patternGroups.set(e.aml_pattern_matched, group)
    }
  }

  for (const [pattern, members] of patternGroups.entries()) {
    // Fully connect within each pattern group (star topology if >3, chain if ≤3)
    // Use a spanning tree to avoid O(n²) edge explosion with large groups
    // Star: first node connects to all others — readable and avoids clutter
    if (members.length >= 2) {
      const hub = members[0]
      for (let i = 1; i < members.length; i++) {
        edges.push({
          source:       hub,
          target:       members[i],
          relationship: `co-flagged: ${pattern}`,
          weight:       0.5 + 0.5 * (i === 1 ? 1 : 0.5), // hub-spoke weight
          pattern:      pattern as AmlPattern,
        })
      }
    }
  }

  // Distinct patterns
  const patterns: AmlPattern[] = [
    ...new Set(entities.map(e => e.aml_pattern_matched).filter(Boolean))
  ] as AmlPattern[]

  const hasSmurfing = entities.some(e => e.aml_pattern_matched === 'smurfing')

  return {
    nodes,
    edges,
    patterns,
    hasSmurfing,
    stats: {
      totalNodes:  nodes.length,
      highRisk:    nodes.filter(n => n.risk_band === 'High').length,
      mediumRisk:  nodes.filter(n => n.risk_band === 'Medium').length,
      lowRisk:     nodes.filter(n => n.risk_band === 'Low').length,
      edgeCount:   edges.length,
    },
  }
}

/**
 * Filter GraphData by risk band and/or AML pattern.
 * Returns a new GraphData with only matching nodes and edges between them.
 */
export function filterGraphData(
  data: GraphData,
  opts: { riskBand?: RiskBand | 'all'; pattern?: AmlPattern | 'all' }
): GraphData {
  const { riskBand = 'all', pattern = 'all' } = opts

  const filteredNodes = data.nodes.filter(n => {
    if (riskBand !== 'all' && n.risk_band !== riskBand) return false
    if (pattern !== 'all' && n.aml_pattern !== pattern) return false
    return true
  })

  const filteredIds = new Set(filteredNodes.map(n => n.id))

  const filteredEdges = data.edges.filter(
    e => filteredIds.has(e.source) && filteredIds.has(e.target)
  )

  return {
    ...data,
    nodes:  filteredNodes,
    edges:  filteredEdges,
    stats: {
      ...data.stats,
      totalNodes: filteredNodes.length,
      edgeCount:  filteredEdges.length,
      highRisk:   filteredNodes.filter(n => n.risk_band === 'High').length,
      mediumRisk: filteredNodes.filter(n => n.risk_band === 'Medium').length,
      lowRisk:    filteredNodes.filter(n => n.risk_band === 'Low').length,
    },
  }
}
