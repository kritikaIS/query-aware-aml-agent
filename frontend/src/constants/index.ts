/**
 * Application-wide constants
 * Documented Requirements: §5.1 quick-select chips (3 reference queries from Solution Design §9)
 */

import type { QuickSelectChip } from '@/types'

// ── API ─────────────────────────────────────────────────────────────
// Fix #48: single source of truth — read from env.ts, not redeclared here
import { env } from '@/config'
export const API_BASE_URL = env.apiBaseUrl

// ── Quick-select chips (§5.1) ────────────────────────────────────────
// These are the EXACT three reference queries from Solution Design §9 Demo Plan
// One click = judge sees the full range of adaptive behaviour without typing
export const QUICK_SELECT_CHIPS: QuickSelectChip[] = [
  {
    label: 'Analyse dataset',
    query: 'Analyse this dataset for suspicious activity',
  },
  {
    label: '10+ txns under $10k',
    query: 'Which customers made 10+ transactions under $10,000?',
  },
  {
    label: 'Customer 4521 suspicious?',
    query: 'Is customer ID 4521 suspicious?',
  },
]

// ── Tool names (matches backend tool registry) ───────────────────────
export const TOOL_NAMES = {
  DATA_LOADER:        'data_loader',
  EDA_TOOL:           'eda_tool',
  FEATURE_ENGINEERING:'feature_engineering',
  ANOMALY_DETECTION:  'anomaly_detection',
  RISK_CLASSIFICATION:'risk_classification',
  ESCALATION:         'escalation',
  EXPLANATION:        'explanation',
} as const

// Human-readable labels per tool card (§5.2)
export const TOOL_LABELS: Record<string, string> = {
  data_loader:         'DATA LOADER',
  eda_tool:            'EDA',
  feature_engineering: 'FEATURE ENG.',
  anomaly_detection:   'DETECTION',
  risk_classification: 'RISK CLASS.',
  escalation:          'ESCALATION',
  explanation:         'EXPLAIN (LLM)',
}

// ── Risk band colors (CSS variable names, §4.1) ──────────────────────
export const RISK_COLOR: Record<string, string> = {
  Low:    'var(--risk-low)',
  Medium: 'var(--risk-medium)',
  High:   'var(--risk-high)',
}

// ── Animation / motion (§7.1) ────────────────────────────────────────
export const MOTION = {
  INSTANT:      0.1,   // seconds
  FAST:         0.18,
  BASE:         0.3,
  SLOW:         0.5,
  STREAM_MS:    28,    // ms per character for typewriter
  STAGGER_DELAY: 0.06, // seconds between card stagger (§7.2 seq 1)
  BREATHING_DURATION: 2.4, // seconds for planning pulse (§7.3)
} as const

// ── Performance budget (§13) ─────────────────────────────────────────
export const PERF = {
  FIRST_CARD_MS:    800,
  PLAN_ANIM_MAX_MS: 3000,
  REPORT_RENDER_MS: 300,
} as const

// ── Responsive breakpoints in px (§9) ───────────────────────────────
export const BREAKPOINTS = {
  MOBILE:  0,
  TABLET:  768,
  DESKTOP: 1280,
} as const
