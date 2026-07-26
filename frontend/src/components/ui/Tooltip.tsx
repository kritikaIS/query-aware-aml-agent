/**
 * Tooltip — hover tooltip
 * Documented Requirement: §10 skip-reason text always in accessibility tree;
 * §8 every chart exposes hover tooltip citing source row/feature.
 */

import React, { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { cn } from '@/utils'

interface TooltipProps {
  content: React.ReactNode
  children: React.ReactElement
  placement?: 'top' | 'bottom' | 'left' | 'right'
  className?: string
  /** When true, tooltip content is always in the accessibility tree (§10) */
  alwaysInTree?: boolean
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  placement = 'top',
  className,
  alwaysInTree = false,
}) => {
  const [visible, setVisible] = useState(false)

  const placementClasses: Record<string, string> = {
    top:    'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left:   'right-full top-1/2 -translate-y-1/2 mr-2',
    right:  'left-full top-1/2 -translate-y-1/2 ml-2',
  }

  const tooltipId = React.useId()

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
      {React.cloneElement(children, { 'aria-describedby': tooltipId } as any)}

      {/* Always-in-tree version (§10): visually hidden when not hovered */}
      {alwaysInTree && (
        <span id={tooltipId} className="sr-only">{content}</span>
      )}

      <AnimatePresence>
        {visible && (
          <motion.span
            id={!alwaysInTree ? tooltipId : undefined}
            role="tooltip"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1, transition: { duration: 0.1 } }}
            exit={{ opacity: 0, transition: { duration: 0.1 } }}
            className={cn(
              'absolute z-tooltip pointer-events-none',
              'px-2.5 py-1.5 rounded-md',
              'bg-bg-panel-raised border border-border-hairline',
              'text-xs text-text-primary whitespace-nowrap',
              'shadow-raised',
              placementClasses[placement],
              className
            )}
          >
            {content}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  )
}
