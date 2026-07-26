/**
 * ToolProgressBar — horizontal progress bar inside ToolCard
 * Documented Requirement: §5.2 "live progress bar" per active card
 * §13: never animates width directly — uses scaleX transform on inner fill
 */

import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'
import type { ToolState } from '@/types'

interface ToolProgressBarProps {
  progress: number    // 0–100
  state:    ToolState
  isLlm?:  boolean
}

export const ToolProgressBar: React.FC<ToolProgressBarProps> = ({
  progress,
  state,
  isLlm = false,
}) => {
  const reduced   = useReducedMotion()
  const isDone    = state === 'done'
  const isQueued  = state === 'queued'
  const isError   = state === 'error'

  const fillColor = isError
    ? 'bg-risk-high'
    : isDone
      ? 'bg-risk-low'
      : isLlm
        ? 'bg-accent-violet'
        : 'bg-accent-cyan'

  const pct = isDone ? 100 : isQueued ? 0 : Math.min(progress, 100)

  return (
    <div
      className={cn(
        'relative h-1 w-full rounded-full overflow-hidden',
        'bg-border-hairline'
      )}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      aria-label={`${pct}% complete`}
    >
      <motion.div
        className={cn('absolute inset-y-0 left-0 rounded-full', fillColor)}
        // §13: use scaleX on a full-width element (transform only, not width)
        style={{ width: '100%', transformOrigin: 'left center' }}
        animate={{ scaleX: pct / 100 }}
        transition={
          reduced
            ? { duration: 0 }
            : { duration: 0.3, ease: [0.2, 0, 0, 1] }
        }
      />
    </div>
  )
}
