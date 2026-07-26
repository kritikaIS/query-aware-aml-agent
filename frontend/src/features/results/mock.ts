/**
 * Mock ExecutionReport for the Results Dashboard (Screen ③).
 * Documented Requirement: §12 — ResultsDashboard hydrates from ExecutionReport.
 * Values match the §5.3 wireframe exactly (48,213 txns, 17 entities, 3 High 9 Med 5 Low).
 * Customer IDs and scores match §8 Output Report Schema examples.
 */

import type { ExecutionReport } from '@/types'
import { MOCK_QUERY_SPEC, MOCK_EXECUTION_PLAN } from '@/features/plan/mock'

export const MOCK_EXECUTION_REPORT: ExecutionReport = {
  user_query:      'Find structuring patterns in the last 30 days',
  query_spec:      MOCK_QUERY_SPEC,
  execution_plan:  MOCK_EXECUTION_PLAN,

  summary_metrics: {
    total_transactions_scanned: 48213,   // §5.3 wireframe
    entities_flagged:           17,       // §5.3 wireframe
    high_risk:                  3,        // §5.3 wireframe
    medium_risk:                9,        // §5.3 wireframe
    low_risk:                   5,        // §5.3 wireframe
  },

  flagged_entities: [
    // ── HIGH RISK ──────────────────────────────────────────────────
    {
      customer_id:         '4521',
      risk_score:          0.87,
      risk_band:           'High',
      aml_pattern_matched: 'structuring',
      top_contributing_features: [
        { feature: 'near_threshold_txn_count_7d', value: 6,   z_score: 3.1 },
        { feature: 'avg_txn_amount_deviation',    value: 2.4, z_score: 2.4 },
      ],
      explanation:
        'Customer 4521 made 6 deposits of $9,200–$9,800 within 7 days — just under the $10,000 reporting threshold, consistent with structuring.',
      recommended_action: 'Report (SAR draft)',
    },
    {
      customer_id:         '7832',
      risk_score:          0.81,
      risk_band:           'High',
      aml_pattern_matched: 'structuring',
      top_contributing_features: [
        { feature: 'near_threshold_txn_count_7d', value: 5,   z_score: 2.9 },
        { feature: 'velocity_score',              value: 1.8, z_score: 2.1 },
      ],
      explanation:
        'Customer 7832 made 5 near-threshold deposits across 3 days, suggesting deliberate structuring behaviour.',
      recommended_action: 'Report (SAR draft)',
    },
    {
      customer_id:         '1190',
      risk_score:          0.79,
      risk_band:           'High',
      aml_pattern_matched: 'structuring',
      top_contributing_features: [
        { feature: 'near_threshold_txn_count_30d', value: 8,   z_score: 3.4 },
        { feature: 'avg_txn_amount_deviation',     value: 1.9, z_score: 2.0 },
      ],
      explanation:
        'Customer 1190 has the highest near-threshold transaction count over 30 days in the filtered cohort.',
      recommended_action: 'Report (SAR draft)',
    },

    // ── MEDIUM RISK ────────────────────────────────────────────────
    {
      customer_id:         '2290',
      risk_score:          0.61,
      risk_band:           'Medium',
      aml_pattern_matched: 'smurfing',
      top_contributing_features: [
        { feature: 'fan_out_ratio',  value: 4.2, z_score: 1.9 },
        { feature: 'velocity_score', value: 1.1, z_score: 1.4 },
      ],
      explanation:
        'Customer 2290 distributed funds to 4 counterparties in rapid succession — consistent with smurfing.',
      recommended_action: 'Flag for review',
    },
    {
      customer_id:         '3041',
      risk_score:          0.58,
      risk_band:           'Medium',
      aml_pattern_matched: 'structuring',
      top_contributing_features: [
        { feature: 'near_threshold_txn_count_7d', value: 3, z_score: 1.7 },
      ],
      explanation: 'Customer 3041 made 3 near-threshold deposits in a 7-day window.',
      recommended_action: 'Flag for review',
    },
    {
      customer_id:         '5503',
      risk_score:          0.55,
      risk_band:           'Medium',
      aml_pattern_matched: 'layering',
      top_contributing_features: [
        { feature: 'hop_count',      value: 3,   z_score: 1.6 },
        { feature: 'fan_out_ratio',  value: 2.8, z_score: 1.5 },
      ],
      explanation:
        'Customer 5503 shows a 3-hop fund transfer pattern through intermediate accounts.',
      recommended_action: 'Flag for review',
    },
    {
      customer_id:         '6712',
      risk_score:          0.52,
      risk_band:           'Medium',
      aml_pattern_matched: 'structuring',
      top_contributing_features: [
        { feature: 'near_threshold_txn_count_7d', value: 3, z_score: 1.5 },
      ],
      explanation: 'Customer 6712 has 3 transactions just below the $10,000 threshold.',
      recommended_action: 'Flag for review',
    },
    {
      customer_id:         '8801',
      risk_score:          0.49,
      risk_band:           'Medium',
      aml_pattern_matched: 'structuring',
      top_contributing_features: [
        { feature: 'velocity_score', value: 1.2, z_score: 1.4 },
      ],
      explanation: 'Customer 8801 has elevated transaction velocity with moderate amounts.',
      recommended_action: 'Flag for review',
    },
    {
      customer_id:         '9023',
      risk_score:          0.47,
      risk_band:           'Medium',
      aml_pattern_matched: null,
      top_contributing_features: [
        { feature: 'avg_txn_amount_deviation', value: 1.5, z_score: 1.3 },
      ],
      explanation: 'Customer 9023 shows statistically elevated amount deviations from peer group.',
      recommended_action: 'Flag for review',
    },
    {
      customer_id:         '0345',
      risk_score:          0.44,
      risk_band:           'Medium',
      aml_pattern_matched: 'rapid_cashout',
      top_contributing_features: [
        { feature: 'cashout_time_delta', value: 0.8, z_score: 1.3 },
      ],
      explanation: 'Customer 0345 withdraws funds rapidly after deposits.',
      recommended_action: 'Flag for review',
    },
    {
      customer_id:         '1456',
      risk_score:          0.41,
      risk_band:           'Medium',
      aml_pattern_matched: 'structuring',
      top_contributing_features: [
        { feature: 'near_threshold_txn_count_7d', value: 2, z_score: 1.2 },
      ],
      explanation: 'Customer 1456 has 2 near-threshold transactions in the period.',
      recommended_action: 'Flag for review',
    },
    {
      customer_id:         '2567',
      risk_score:          0.40,
      risk_band:           'Medium',
      aml_pattern_matched: null,
      top_contributing_features: [
        { feature: 'velocity_score', value: 0.9, z_score: 1.2 },
      ],
      explanation: 'Customer 2567 shows mildly elevated velocity with no clear pattern match.',
      recommended_action: 'Flag for review',
    },

    // ── LOW RISK ───────────────────────────────────────────────────
    {
      customer_id:         '8813',
      risk_score:          0.22,
      risk_band:           'Low',
      aml_pattern_matched: null,
      top_contributing_features: [
        { feature: 'avg_txn_amount_deviation', value: 0.6, z_score: 0.8 },
      ],
      explanation: 'Customer 8813 shows minor deviations within expected range.',
      recommended_action: 'Monitor',
    },
    {
      customer_id:         '3678',
      risk_score:          0.19,
      risk_band:           'Low',
      aml_pattern_matched: null,
      top_contributing_features: [],
      explanation: 'Customer 3678 has low risk indicators across all feature families.',
      recommended_action: 'Monitor',
    },
    {
      customer_id:         '4789',
      risk_score:          0.17,
      risk_band:           'Low',
      aml_pattern_matched: null,
      top_contributing_features: [],
      explanation: 'Customer 4789 is within normal transactional patterns.',
      recommended_action: 'Monitor',
    },
    {
      customer_id:         '5890',
      risk_score:          0.14,
      risk_band:           'Low',
      aml_pattern_matched: null,
      top_contributing_features: [],
      explanation: 'Customer 5890 has minimal AML indicators in the 30-day window.',
      recommended_action: 'Monitor',
    },
    {
      customer_id:         '6901',
      risk_score:          0.11,
      risk_band:           'Low',
      aml_pattern_matched: null,
      top_contributing_features: [],
      explanation: 'Customer 6901 shows no significant anomaly signals.',
      recommended_action: 'Monitor',
    },
  ],

  charts: [],  // chart data is inline in components for mock
}

// ── Mocked transaction histogram data (§8 ThresholdHistogram) ──────────
// Values clustered just below $10,000 — the structuring signal
export const MOCK_HISTOGRAM_DATA = [
  { bin: '$0–$2k',   count: 312  },
  { bin: '$2k–$4k',  count: 487  },
  { bin: '$4k–$6k',  count: 623  },
  { bin: '$6k–$8k',  count: 891  },
  { bin: '$8k–$9k',  count: 1204 },
  { bin: '$9k–$9.5k',count: 1876 },
  { bin: '$9.5k–$10k',count: 2341 },  // ← cluster just under $10k threshold
  { bin: '$10k+',    count: 198  },   // ← sharp drop above threshold
]

// ── Mocked timeline scatter data (§8 TimelineScatter) ──────────────────
// Flagged transactions over time; point_size = amount; near-threshold get halo
export const MOCK_TIMELINE_DATA = [
  { date: '2026-06-25', amount: 9800, customer_id: '4521', flagged: true,  near_threshold: true  },
  { date: '2026-06-26', amount: 9650, customer_id: '4521', flagged: true,  near_threshold: true  },
  { date: '2026-06-27', amount: 9200, customer_id: '4521', flagged: true,  near_threshold: true  },
  { date: '2026-06-28', amount: 4200, customer_id: '3041', flagged: true,  near_threshold: false },
  { date: '2026-06-29', amount: 9500, customer_id: '7832', flagged: true,  near_threshold: true  },
  { date: '2026-06-30', amount: 9700, customer_id: '7832', flagged: true,  near_threshold: true  },
  { date: '2026-07-01', amount: 9100, customer_id: '4521', flagged: true,  near_threshold: true  },
  { date: '2026-07-03', amount: 2800, customer_id: '8813', flagged: false, near_threshold: false },
  { date: '2026-07-05', amount: 9800, customer_id: '1190', flagged: true,  near_threshold: true  },
  { date: '2026-07-07', amount: 9600, customer_id: '1190', flagged: true,  near_threshold: true  },
  { date: '2026-07-09', amount: 9300, customer_id: '1190', flagged: true,  near_threshold: true  },
  { date: '2026-07-11', amount: 5500, customer_id: '2290', flagged: true,  near_threshold: false },
  { date: '2026-07-13', amount: 9750, customer_id: '4521', flagged: true,  near_threshold: true  },
  { date: '2026-07-15', amount: 9400, customer_id: '1190', flagged: true,  near_threshold: true  },
  { date: '2026-07-17', amount: 3200, customer_id: '6901', flagged: false, near_threshold: false },
  { date: '2026-07-19', amount: 9900, customer_id: '7832', flagged: true,  near_threshold: true  },
  { date: '2026-07-21', amount: 9250, customer_id: '4521', flagged: true,  near_threshold: true  },
  { date: '2026-07-22', amount: 9550, customer_id: '1190', flagged: true,  near_threshold: true  },
  { date: '2026-07-23', amount: 8100, customer_id: '6712', flagged: true,  near_threshold: false },
  { date: '2026-07-24', amount: 9850, customer_id: '7832', flagged: true,  near_threshold: true  },
]
