/**
 * RiskDonut — §6 Component Library
 * States: default · filtered
 * Documented Requirement: §5.3 "Risk-split donut is clickable and cross-filters
 * the flagged-entity table (click 'High' → table filters to High only)"
 * §8: "Fixed color mapping (low/med/high) never changes across screens"
 * §8: "Recharts / Plotly" — using Recharts per §11 "Recharts (KPI/donut/bars)"
 * §8 design contract: risk-band colors never reused for anything else
 */

import React from 'react'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'
import type { RiskFilter, SummaryMetrics } from '@/types'

// Recharts is code-split via vite.config.ts manualChunks — no need for lazy() here.
// Static import is safe; the recharts chunk only loads when this component renders.
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface RiskDonutProps {
  metrics:      SummaryMetrics
  activeFilter: RiskFilter
  onFilter:     (filter: RiskFilter) => void
  size?:        number
}

const DONUT_DATA_FROM_METRICS = (m: SummaryMetrics) => [
  { name: 'High',   value: m.high_risk,   color: 'var(--risk-high)',   filter: 'High'   as RiskFilter },
  { name: 'Medium', value: m.medium_risk, color: 'var(--risk-medium)', filter: 'Medium' as RiskFilter },
  { name: 'Low',    value: m.low_risk,    color: 'var(--risk-low)',    filter: 'Low'    as RiskFilter },
]

// Custom tooltip matching §8 design contract (axis labels in --text-secondary)
const DonutTooltip: React.FC<{ active?: boolean; payload?: Array<{ name: string; value: number; payload: { color: string } }> }> = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const { name, value, payload: p } = payload[0]
  return (
    <div className="panel px-2.5 py-1.5 text-xs shadow-raised">
      <span className="font-mono" style={{ color: p.color }}>{name}</span>
      <span className="text-text-secondary ml-2">{value} entities</span>
    </div>
  )
}

export const RiskDonut: React.FC<RiskDonutProps> = ({
  metrics,
  activeFilter,
  onFilter,
  size = 80,
}) => {
  const reduced = useReducedMotion()
  const data    = DONUT_DATA_FROM_METRICS(metrics)

  const handleClick = (entry: { filter: RiskFilter }) => {
    // Toggle: click same filter → clear to 'all'
    onFilter(activeFilter === entry.filter ? 'all' : entry.filter)
  }

  return (
    <div
      role="img"
      aria-label={`Risk split: ${metrics.high_risk} High, ${metrics.medium_risk} Medium, ${metrics.low_risk} Low`}
    >
        <ResponsiveContainer width={size} height={size}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={size * 0.32}
              outerRadius={size * 0.48}
              paddingAngle={2}
              dataKey="value"
              animationBegin={0}
              animationDuration={reduced ? 0 : 500}
              onClick={(entry: { filter: RiskFilter }) => handleClick(entry)}
              style={{ cursor: 'pointer' }}
            >
              {data.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={entry.color}
                  opacity={
                    activeFilter === 'all' || activeFilter === entry.filter
                      ? 1
                      : 0.25     // dim non-selected segments when filter active
                  }
                  stroke="var(--bg-void)"
                  strokeWidth={2}
                  aria-label={`${entry.name} risk: ${entry.value} entities. Click to filter.`}
                />
              ))}
            </Pie>
            <Tooltip content={<DonutTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
  )
}

// ── Inline legend next to donut (§5.3 "3 🔴 9 🟡 5 🟢") ──────────────
interface DonutLegendProps {
  metrics:      SummaryMetrics
  activeFilter: RiskFilter
  onFilter:     (filter: RiskFilter) => void
}

export const DonutLegend: React.FC<DonutLegendProps> = ({ metrics, activeFilter, onFilter }) => {
  const items = [
    { band: 'High'   as RiskFilter, count: metrics.high_risk,   color: 'text-risk-high',   bg: 'bg-risk-high/10',   border: 'border-risk-high/30'   },
    { band: 'Medium' as RiskFilter, count: metrics.medium_risk, color: 'text-risk-medium', bg: 'bg-risk-medium/10', border: 'border-risk-medium/30' },
    { band: 'Low'    as RiskFilter, count: metrics.low_risk,    color: 'text-risk-low',    bg: 'bg-risk-low/10',   border: 'border-risk-low/30'    },
  ]

  return (
    <div className="flex flex-col gap-1.5" role="group" aria-label="Risk filter controls">
      {items.map(({ band, count, color, bg, border }) => {
        const isActive = activeFilter === band
        return (
          <button
            key={band}
            type="button"
            onClick={() => onFilter(activeFilter === band ? 'all' : band)}
            aria-pressed={isActive}
            aria-label={`Filter by ${band} risk (${count} entities)`}
            className={cn(
              'flex items-center gap-2 px-2 py-1 rounded-md text-left w-full',
              'transition-all duration-[100ms] border',
              isActive
                ? cn(bg, border, color, 'font-semibold')
                : 'border-transparent hover:bg-bg-panel-raised text-text-secondary hover:text-text-primary',
              'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan',
              'cursor-pointer'
            )}
          >
            <span className={cn('text-[10px]', color)} aria-hidden>●</span>
            <span className="text-xs">{band}</span>
            <span className={cn('ml-auto text-xs font-mono', isActive ? color : 'text-text-secondary')}>
              {count}
            </span>
          </button>
        )
      })}
    </div>
  )
}
