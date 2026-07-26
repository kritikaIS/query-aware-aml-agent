/**
 * QueryChip — quick-select chip for the three reference queries.
 * Documented Requirement: §5.1 "Three quick-select chips pre-load the exact
 * three reference queries from the Solution Design §9 demo plan"
 *
 * Animations:
 * - motion-instant (100ms ease-out) hover lift (§7.1)
 * - focus ring: accent-cyan (§4.1, §10)
 * Accessibility: keyboard activatable via Enter/Space (§10)
 */

import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'

interface QueryChipProps {
  label: string
  onClick: () => void
  disabled?: boolean
}

export const QueryChip: React.FC<QueryChipProps> = ({ label, onClick, disabled }) => {
  const reduced = useReducedMotion()

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      if (!disabled) onClick()
    }
  }

  return (
    <motion.button
      type="button"
      onClick={disabled ? undefined : onClick}
      onKeyDown={handleKeyDown}
      disabled={disabled}
      // Hover lift: motion-instant (100ms) — §7.1
      whileHover={reduced || disabled ? {} : { scale: 1.02, y: -1 }}
      whileTap={reduced || disabled ? {} : { scale: 0.98 }}
      transition={{ duration: 0.1, ease: 'easeOut' }}
      className={cn(
        // Surface: bg-panel-raised, hairline border
        'inline-flex items-center gap-1.5 px-3 py-1.5',
        'rounded-md text-sm font-medium',
        'bg-bg-panel border border-border-hairline',
        'text-text-secondary',
        // Hover: lift to panel-raised, text brightens
        'hover:bg-bg-panel-raised hover:text-text-primary hover:border-accent-cyan/40',
        'transition-colors duration-[100ms] ease-out',
        // Focus ring: accent-cyan (§4.1, §10)
        'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan focus-visible:border-accent-cyan',
        // Disabled
        disabled && 'opacity-40 cursor-not-allowed pointer-events-none',
        'cursor-pointer'
      )}
      aria-label={`Run query: ${label}`}
    >
      <span className="text-text-secondary text-xs">›</span>
      {label}
    </motion.button>
  )
}
