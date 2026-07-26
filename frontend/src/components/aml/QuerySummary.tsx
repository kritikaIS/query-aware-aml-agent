/**
 * QuerySummary — shows ① Intent Parsed section at top of Plan Visualizer
 * Documented Requirement: §5.2 wireframe:
 *   ① Intent Parsed → pattern_detection · structuring
 *      filters: date_range = last 30d
 *
 * §4.1: accent-violet for LLM/reasoning elements
 * §4.2: monospace for machine values (intent type, pattern, filter values)
 */

import React from 'react'
import { Brain } from 'lucide-react'
import { cn } from '@/utils'
import type { QuerySpec } from '@/types'

interface QuerySummaryProps {
  query:     string
  querySpec: QuerySpec | null
  /** True while the intent is still being parsed */
  parsing?:  boolean
}

export const QuerySummary: React.FC<QuerySummaryProps> = ({
  query,
  querySpec,
  parsing = false,
}) => {
  return (
    <div className="flex flex-col gap-3">
      {/* ── Submitted query in quotes (§5.2 header) ── */}
      <div>
        <h2 className="text-base font-semibold text-text-primary leading-snug">
          <span className="text-text-secondary font-normal mr-1">"</span>
          {query}
          <span className="text-text-secondary font-normal ml-1">"</span>
        </h2>
      </div>

      {/* ── ① Intent Parsed row (§5.2) ── */}
      <div
        className={cn(
          'flex flex-col gap-1.5 px-4 py-3 rounded-lg border',
          'bg-bg-panel border-accent-violet/20',
          'transition-all duration-[300ms]'
        )}
      >
        {/* Row header */}
        <div className="flex items-center gap-2">
          <Brain size={12} className="text-accent-violet shrink-0" aria-hidden />
          <span className="text-[11px] font-semibold text-accent-violet uppercase tracking-wider">
            ① Intent Parsed
          </span>
          {parsing && (
            <span className="text-[10px] font-mono text-text-secondary animate-pulse">
              parsing…
            </span>
          )}
        </div>

        {querySpec && (
          <>
            {/* Intent + pattern — §5.2 wireframe: "pattern_detection · structuring" */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-mono text-text-primary bg-bg-panel-raised px-2 py-0.5 rounded border border-border-hairline">
                {querySpec.intent}
              </span>
              {querySpec.aml_pattern && (
                <>
                  <span className="text-text-secondary text-xs">·</span>
                  <span className="text-xs font-mono text-accent-cyan bg-accent-cyan/5 px-2 py-0.5 rounded border border-accent-cyan/20">
                    {querySpec.aml_pattern}
                  </span>
                </>
              )}
              {querySpec.requires_ml_anomaly_detection && (
                <>
                  <span className="text-text-secondary text-xs">·</span>
                  <span className="text-[10px] font-mono text-text-secondary px-1.5 py-0.5 rounded bg-bg-panel-raised border border-border-hairline">
                    ML
                  </span>
                </>
              )}
            </div>

            {/* Filters — §5.2 wireframe: "filters: date_range = last 30d" */}
            {querySpec.filters.date_range && (
              <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                <span className="font-medium">filters:</span>
                <span className="font-mono text-text-primary">
                  date_range
                </span>
                <span className="text-text-secondary">=</span>
                <span className="font-mono text-text-primary">
                  {querySpec.filters.date_range.start}
                  <span className="text-text-secondary mx-1">→</span>
                  {querySpec.filters.date_range.end}
                </span>
              </div>
            )}
            {querySpec.filters.customer_id && (
              <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                <span className="font-medium">filters:</span>
                <span className="font-mono text-text-primary">customer_id</span>
                <span className="text-text-secondary">=</span>
                <span className="font-mono text-accent-cyan">{querySpec.filters.customer_id}</span>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
