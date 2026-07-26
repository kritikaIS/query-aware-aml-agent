/**
 * FilterBar — sort control for the Flagged Entities table
 * Documented Requirement: §5.3 "sort: risk ▾"
 * Supports sorting by risk_score (default desc), customer_id, aml_pattern
 */

import React from 'react'
import { ArrowDownUp } from 'lucide-react'
import { cn } from '@/utils'
import type { SortConfig, RiskFilter } from '@/types'

interface FilterBarProps {
  sortConfig:    SortConfig
  onSortChange:  (config: SortConfig) => void
  entityCount:   number
  filteredCount: number
  activeFilter:  RiskFilter
}

const SORT_OPTIONS = [
  { field: 'risk_score',   label: 'Risk ▾' },
  { field: 'customer_id',  label: 'Customer ID' },
]

export const FilterBar: React.FC<FilterBarProps> = ({
  sortConfig,
  onSortChange,
  entityCount,
  filteredCount,
  activeFilter,
}) => {
  const handleSort = (field: string) => {
    if (sortConfig.field === field) {
      // Toggle direction
      onSortChange({ field, direction: sortConfig.direction === 'desc' ? 'asc' : 'desc' })
    } else {
      onSortChange({ field, direction: 'desc' })
    }
  }

  return (
    <div className="flex items-center justify-between gap-3 flex-wrap">
      {/* Left: label + count */}
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold text-text-primary">
          Flagged Entities
        </h2>
        <span className="text-[11px] font-mono text-text-secondary">
          {activeFilter !== 'all'
            ? `${filteredCount} of ${entityCount}`
            : entityCount
          }
        </span>
        {activeFilter !== 'all' && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-bg-panel-raised border border-border-hairline text-text-secondary font-mono">
            {activeFilter}
          </span>
        )}
      </div>

      {/* Right: sort controls */}
      <div className="flex items-center gap-1" role="group" aria-label="Sort options">
        <span className="text-xs text-text-secondary mr-1 hidden tablet:inline">
          <ArrowDownUp size={11} className="inline mr-1" aria-hidden />
          sort:
        </span>
        {SORT_OPTIONS.map(({ field, label }) => {
          const active    = sortConfig.field === field
          const isDesc    = sortConfig.direction === 'desc'
          return (
            <button
              key={field}
              type="button"
              onClick={() => handleSort(field)}
              aria-pressed={active}
              aria-label={`Sort by ${label} ${active ? (isDesc ? 'descending' : 'ascending') : ''}`}
              className={cn(
                'px-2.5 py-1 rounded text-xs font-medium',
                'border transition-colors duration-[100ms]',
                active
                  ? 'bg-accent-cyan/10 border-accent-cyan/30 text-accent-cyan'
                  : 'bg-bg-panel border-border-hairline text-text-secondary hover:bg-bg-panel-raised hover:text-text-primary',
                'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan',
                'cursor-pointer'
              )}
            >
              {label}
              {active && (
                <span className="ml-1 font-mono text-[9px]">
                  {isDesc ? '↓' : '↑'}
                </span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
