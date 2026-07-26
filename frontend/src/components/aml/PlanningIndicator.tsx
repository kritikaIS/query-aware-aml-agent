/**
 * PlanningIndicator — §5.2 wireframe row ②
 * "② Building execution plan...  ▓▓▓▓▓▓▓▓░░  reasoning..."
 *
 * Documented Requirements:
 * - §7.3: the ONE allowed infinite animation — 2.4s breathing pulse
 * - Shows while isPlanning = true, disappears when plan_complete
 * - §4.1: accent-cyan for "agent active thinking"
 */

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'
import { breathingPulseVariants } from '@/animations'
import { MOTION } from '@/constants'

interface PlanningIndicatorProps {
  isPlanning:  boolean
  toolCount?:  number  // how many tools have been assembled so far
  totalTools?: number  // total expected tools
}

export const PlanningIndicator: React.FC<PlanningIndicatorProps> = ({
  isPlanning,
  toolCount  = 0,
  totalTools = 6,
}) => {
  const reduced = useReducedMotion()
  const progress = totalTools > 0 ? (toolCount / totalTools) * 100 : 0

  return (
    <AnimatePresence>
      {isPlanning && (
        <motion.div
          key="planning-indicator"
          initial={{ opacity: 0, y: reduced ? 0 : -8 }}
          animate={{ opacity: 1, y: 0, transition: { duration: MOTION.BASE } }}
          exit={{   opacity: 0, y: reduced ? 0 : -4, transition: { duration: MOTION.FAST } }}
          className={cn(
            'flex items-center gap-3 px-4 py-3 rounded-lg',
            'bg-bg-panel border border-accent-cyan/20'
          )}
          role="status"
          aria-live="polite"
          aria-label="Building execution plan"
        >
          {/* §7.3: the ONE allowed looping animation — breathing pulse on the planning indicator */}
          <motion.span
            variants={breathingPulseVariants}
            animate={reduced ? {} : 'pulse'}
            className="size-2 rounded-full bg-accent-cyan shrink-0"
            aria-hidden
          />

          {/* Label */}
          <span className="text-xs font-medium text-accent-cyan">
            ② Building execution plan
          </span>

          {/* Progress bar — §5.2 wireframe "▓▓▓▓▓▓▓▓░░" */}
          <div
            className="flex-1 max-w-32 h-1.5 rounded-full bg-border-hairline overflow-hidden"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(progress)}
          >
            <motion.div
              className="h-full bg-accent-cyan rounded-full"
              style={{ width: '100%', transformOrigin: 'left center' }}
              animate={{ scaleX: progress / 100 }}
              transition={reduced ? { duration: 0 } : { duration: 0.4, ease: 'easeOut' }}
            />
          </div>

          {/* Tool count */}
          {toolCount > 0 && (
            <span className="text-[11px] font-mono text-text-secondary shrink-0">
              {toolCount}/{totalTools} tools
            </span>
          )}

          <span className="text-[11px] text-text-secondary animate-pulse shrink-0">
            reasoning…
          </span>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
