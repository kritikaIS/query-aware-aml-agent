/**
 * NetworkFilters — risk band + AML pattern filter pills
 * §10: aria-pressed on toggle buttons
 */
import React from 'react'
import { cn } from '@/utils'
import type { RiskBand, AmlPattern } from '@/types'

const PATTERN_LABEL: Record<string, string> = {
  structuring:   'Structuring',
  smurfing:      'Smurfing',
  layering:      'Layering',
  rapid_cashout: 'Cashout',
}

interface NetworkFiltersProps {
  patterns:       AmlPattern[]
  activePattern:  AmlPattern | 'all'
  onPattern:      (p: AmlPattern | 'all') => void
  activeRisk:     RiskBand | 'all'
  onRisk:         (r: RiskBand | 'all') => void
}

export const NetworkFilters: React.FC<NetworkFiltersProps> = ({
  patterns, activePattern, onPattern, activeRisk, onRisk,
}) => {
  const pill = (active: boolean) =>
    cn(
      'inline-flex items-center h-6 px-2.5 rounded-full text-[11px] font-medium border',
      'cursor-pointer transition-colors duration-[100ms]',
      'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan',
      active
        ? 'bg-accent-cyan/10 border-accent-cyan/40 text-accent-cyan'
        : 'bg-bg-panel border-border-hairline text-text-secondary hover:text-text-primary hover:bg-bg-panel-raised'
    )

  return (
    <div className="flex flex-wrap gap-1.5 items-center">
      {/* Risk filters */}
      {(['all', 'High', 'Medium', 'Low'] as const).map(r => (
        <button
          key={r}
          type="button"
          className={pill(activeRisk === r)}
          onClick={() => onRisk(r)}
          aria-pressed={activeRisk === r}
          aria-label={`Filter by risk: ${r}`}
        >
          {r === 'all' ? 'All risk' : r}
        </button>
      ))}

      {patterns.filter(Boolean).length > 0 && (
        <>
          <span className="text-border-hairline text-xs" aria-hidden>|</span>
          {/* Pattern filters */}
          {patterns.filter(Boolean).map(p => (
            <button
              key={p}
              type="button"
              className={pill(activePattern === p)}
              onClick={() => onPattern(activePattern === p ? 'all' : p)}
              aria-pressed={activePattern === p}
              aria-label={`Filter by pattern: ${PATTERN_LABEL[p!] ?? p}`}
            >
              {PATTERN_LABEL[p!] ?? p}
            </button>
          ))}
          {activePattern !== 'all' && (
            <button
              type="button"
              className={pill(false)}
              onClick={() => onPattern('all')}
              aria-label="Clear pattern filter"
            >
              ✕ clear
            </button>
          )}
        </>
      )}
    </div>
  )
}
