/**
 * ExecutionTimeline — summary strip below the pipeline showing
 * tools invoked vs skipped counts.
 * Documented Requirement: §5.2 plan_complete shows the final execution summary.
 * Shown only after isPlanning = false (plan_complete received).
 */

import React from 'react'
import { motion } from 'framer-motion'
import { CheckCircle2, XCircle } from 'lucide-react'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'
import type { ToolCardModel } from '@/types'

interface ExecutionTimelineProps {
  cards:   ToolCardModel[]
  visible: boolean
}

export const ExecutionTimeline: React.FC<ExecutionTimelineProps> = ({ cards, visible }) => {
  const reduced   = useReducedMotion()
  const invoked   = cards.filter((c) => c.state !== 'skipped')
  const skipped   = cards.filter((c) => c.state === 'skipped')

  if (!visible || cards.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: reduced ? 0 : 8 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.2, 0, 0, 1] } }}
      className={cn(
        'flex flex-wrap items-center gap-4 px-4 py-3 rounded-lg',
        'bg-bg-panel border border-border-hairline'
      )}
      role="region"
      aria-label="Execution summary"
    >
      {/* Invoked */}
      <div className="flex items-center gap-1.5">
        <CheckCircle2 size={12} className="text-risk-low" aria-hidden />
        <span className="text-xs text-text-secondary">
          <span className="font-mono text-text-primary font-medium mr-1">
            {invoked.length}
          </span>
          tool{invoked.length !== 1 ? 's' : ''} invoked
        </span>
      </div>

      <span className="text-border-hairline text-xs">·</span>

      {/* Skipped */}
      <div className="flex items-center gap-1.5">
        <XCircle size={12} className="text-text-secondary" aria-hidden />
        <span className="text-xs text-text-secondary">
          <span className="font-mono text-text-primary font-medium mr-1">
            {skipped.length}
          </span>
          skipped
        </span>
      </div>

      {skipped.length > 0 && (
        <>
          <span className="text-border-hairline text-xs">·</span>
          {/* List skipped tool names + reasons inline */}
          <div className="flex flex-wrap gap-2">
            {skipped.map((c) => (
              <span
                key={c.name}
                className="text-[11px] font-mono text-text-secondary bg-bg-panel-raised px-2 py-0.5 rounded border border-border-hairline line-through"
                title={c.skipReason}
              >
                {c.label}
              </span>
            ))}
          </div>
        </>
      )}
    </motion.div>
  )
}
