/**
 * Risk display utilities
 * Documented Requirement: §4.1 risk colors, §6 RiskBadge, §10 accessibility
 * Color is NEVER the only signal — always paired with icon + text (§10)
 */

import type { RiskBand } from '@/types'

export interface RiskDisplay {
  color: string       // CSS variable reference
  tailwindText: string
  tailwindBg: string
  tailwindBorder: string
  icon: string        // text icon (accessible — paired with label)
  label: string
}

export const RISK_DISPLAY: Record<RiskBand, RiskDisplay> = {
  High: {
    color:          'var(--risk-high)',
    tailwindText:   'text-risk-high',
    tailwindBg:     'bg-risk-high/10',
    tailwindBorder: 'border-risk-high/30',
    icon:           '●',
    label:          'High',
  },
  Medium: {
    color:          'var(--risk-medium)',
    tailwindText:   'text-risk-medium',
    tailwindBg:     'bg-risk-medium/10',
    tailwindBorder: 'border-risk-medium/30',
    icon:           '●',
    label:          'Medium',
  },
  Low: {
    color:          'var(--risk-low)',
    tailwindText:   'text-risk-low',
    tailwindBg:     'bg-risk-low/10',
    tailwindBorder: 'border-risk-low/30',
    icon:           '●',
    label:          'Low',
  },
}

export function getRiskDisplay(band: RiskBand): RiskDisplay {
  return RISK_DISPLAY[band]
}

/**
 * Returns risk band from a raw score using the same
 * percentile mapping referenced in Solution Design §5.5.
 * NOTE: This is ONLY used as a display fallback when band is not
 * present in the payload — the real band always comes from the backend.
 */
export function scoreToBand(score: number): RiskBand {
  if (score >= 0.7) return 'High'
  if (score >= 0.4) return 'Medium'
  return 'Low'
}
