/**
 * EntityRow — §6 Component Library
 * States: collapsed · expanded
 * Documented Requirement: §5.3 "every row expands inline (accordion) before
 * it ever opens the full Entity Deep-Dive drawer"
 * §10: keyboard-navigable; Enter expands; Esc or Enter again collapses
 * §7.1 motion-base (300ms) for accordion expand/collapse
 * Row columns: risk badge · customer ID · score · AML pattern · action ▸
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronRight, ChevronDown } from 'lucide-react'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'
import { RiskBadge } from './RiskBadge'
import { formatScore } from '@/utils'
import type { FlaggedEntity } from '@/types'

interface EntityRowProps {
  entity:        FlaggedEntity
  /** Called when ▸ is clicked — triggers Entity Deep-Dive drawer (not implemented yet) */
  onOpenDrawer?: (customerId: string) => void
  isFirst?:      boolean
  isLast?:       boolean
}

export const EntityRow: React.FC<EntityRowProps> = ({
  entity,
  onOpenDrawer,
  isFirst = false,
  isLast: _isLast = false,
}) => {
  const [expanded, setExpanded] = useState(false)
  const reduced = useReducedMotion()

  const toggleExpand = () => setExpanded((e) => !e)

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      toggleExpand()
    }
    if (e.key === 'Escape' && expanded) {
      e.preventDefault()
      setExpanded(false)
    }
  }

  const actionLabel = entity.recommended_action === 'Report (SAR draft)'
    ? '🔴 Report'
    : entity.recommended_action === 'Flag for review'
      ? '🟡 Review'
      : '🟢 Monitor'

  return (
    <div
      className={cn(
        'border-b border-border-hairline last:border-b-0',
        !isFirst && 'border-t-0',
      )}
    >
      {/* ── Main row ── */}
      <div
        role="row"
        tabIndex={0}
        aria-expanded={expanded}
        onKeyDown={handleKeyDown}
        onClick={toggleExpand}
        className={cn(
          'flex items-center gap-3 px-4 py-3',
          'cursor-pointer select-none',
          'transition-colors duration-[100ms]',
          expanded
            ? 'bg-bg-panel-raised'
            : 'hover:bg-bg-panel-raised',
          'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-accent-cyan',
        )}
        aria-label={`Customer ${entity.customer_id}, ${entity.risk_band} risk, score ${formatScore(entity.risk_score)}${entity.aml_pattern_matched ? `, ${entity.aml_pattern_matched}` : ''}`}
      >
        {/* Risk badge (§10: color + icon + text) */}
        <div className="w-16 shrink-0">
          <RiskBadge band={entity.risk_band} animate size="sm" />
        </div>

        {/* Customer ID — monospace (§4.2: machine-generated value) */}
        <span className="w-28 shrink-0 text-xs font-mono text-text-primary">
          Customer {entity.customer_id}
        </span>

        {/* Score — monospace (§4.2) */}
        <span className="w-16 shrink-0 text-xs font-mono text-text-secondary">
          {formatScore(entity.risk_score)}
        </span>

        {/* AML pattern */}
        <span className="flex-1 text-xs text-text-secondary truncate">
          {entity.aml_pattern_matched
            ? <span className="font-mono text-text-primary">{entity.aml_pattern_matched}</span>
            : <span className="text-text-secondary">—</span>
          }
        </span>

        {/* Recommended action */}
        <span className="hidden tablet:flex w-28 shrink-0 text-xs text-text-secondary">
          {actionLabel}
        </span>

        {/* Expand/collapse indicator + deep-dive arrow */}
        <div className="flex items-center gap-1 shrink-0">
          {/* Accordion toggle */}
          <span className="text-text-secondary" aria-hidden>
            {expanded
              ? <ChevronDown size={13} />
              : <ChevronRight size={13} />
            }
          </span>

          {/* ▸ opens Entity Deep-Dive drawer (§5.3) */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onOpenDrawer?.(entity.customer_id)
            }}
            aria-label={`Open detail view for Customer ${entity.customer_id}`}
            className={cn(
              'p-1 rounded text-text-secondary hover:text-accent-cyan',
              'transition-colors duration-[100ms]',
              'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan',
            )}
          >
            ▸
          </button>
        </div>
      </div>

      {/* ── Inline accordion expansion (§5.3, §7.1 motion-base) ── */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="accordion"
            initial={{ height: 0, opacity: 0 }}
            animate={{
              height: 'auto',
              opacity: 1,
              transition: { duration: reduced ? 0 : 0.3, ease: [0.2, 0, 0, 1] },
            }}
            exit={{
              height: 0,
              opacity: 0,
              transition: { duration: reduced ? 0 : 0.2, ease: 'easeInOut' },
            }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-1 border-t border-border-hairline/50 bg-bg-panel-raised">
              {/* Explanation paragraph */}
              {entity.explanation && (
                <p className="text-sm text-text-secondary leading-relaxed mb-3">
                  {entity.explanation}
                </p>
              )}

              {/* Top features summary */}
              {entity.top_contributing_features.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {entity.top_contributing_features.map((f) => (
                    <span
                      key={f.feature}
                      className="text-[11px] font-mono text-text-secondary bg-bg-panel px-2 py-0.5 rounded border border-border-hairline"
                    >
                      {f.feature}
                      <span className="text-accent-cyan ml-1.5">z={f.z_score.toFixed(1)}</span>
                    </span>
                  ))}
                </div>
              )}

              {/* Recommended action */}
              <div className="mt-3 flex items-center gap-2">
                <span className="text-xs text-text-secondary">Recommended:</span>
                <span className="text-xs font-medium text-text-primary">
                  {entity.recommended_action}
                </span>
              </div>

              {/* Hint to open full deep-dive */}
              <button
                type="button"
                onClick={() => onOpenDrawer?.(entity.customer_id)}
                className="mt-2 text-[11px] text-accent-cyan hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan rounded"
                aria-label={`Open full detail view for Customer ${entity.customer_id}`}
              >
                View full analysis ▸
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
