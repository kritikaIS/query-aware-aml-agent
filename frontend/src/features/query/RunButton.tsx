/**
 * RunButton — the primary action button on the Query Console.
 * Documented Requirement: §5.1 "[ Run Query ▸ ]" — right-aligned, below input.
 *
 * States: idle → loading (simulated 1.5s) → transitions to plan view.
 *
 * Animations:
 * - Hover: opacity lift (motion-instant 100ms) (§7.1)
 * - Click → loading: spinner replaces chevron (motion-fast 180ms) (§7.1)
 *
 * Accessibility:
 * - aria-busy during loading (§10)
 * - aria-label changes by state
 */

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, Loader2 } from 'lucide-react'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'

interface RunButtonProps {
  onClick: () => void
  loading?: boolean
  disabled?: boolean
}

export const RunButton: React.FC<RunButtonProps> = ({ onClick, loading = false, disabled = false }) => {
  const reduced = useReducedMotion()
  const isDisabled = disabled || loading

  return (
    <motion.button
      type="button"
      onClick={isDisabled ? undefined : onClick}
      disabled={isDisabled}
      aria-label={loading ? 'Running query…' : 'Run query'}
      aria-busy={loading}
      // Hover: subtle opacity lift — motion-instant (§7.1)
      whileHover={reduced || isDisabled ? {} : { opacity: 0.9 }}
      whileTap={reduced || isDisabled ? {} : { scale: 0.97 }}
      transition={{ duration: 0.1, ease: 'easeOut' }}
      className={cn(
        'inline-flex items-center gap-2 h-11 px-5',
        'rounded-lg font-semibold text-sm',
        // Primary variant: accent-cyan background, dark text
        'bg-accent-cyan text-bg-void',
        // Transition — motion-fast for state changes (§7.1)
        'transition-all duration-[180ms] ease-[cubic-bezier(0.2,0,0,1)]',
        // Focus ring
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-void',
        // Disabled
        isDisabled && 'opacity-60 cursor-not-allowed',
        !isDisabled && 'cursor-pointer'
      )}
    >
      <AnimatePresence mode="wait" initial={false}>
        {loading ? (
          <motion.span
            key="loading"
            initial={reduced ? { opacity: 1 } : { opacity: 0, rotate: -90 }}
            animate={{ opacity: 1, rotate: 0 }}
            exit={reduced ? { opacity: 1 } : { opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="flex items-center gap-2"
          >
            {/* Loading spinner — motion-fast (§7.1) */}
            <Loader2 size={16} className="animate-spin" aria-hidden />
            <span>Running…</span>
          </motion.span>
        ) : (
          <motion.span
            key="idle"
            initial={reduced ? { opacity: 1 } : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={reduced ? { opacity: 1 } : { opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="flex items-center gap-2"
          >
            <span>Run Query</span>
            {/* ▸ from wireframe §5.1 */}
            <ArrowRight size={15} aria-hidden />
          </motion.span>
        )}
      </AnimatePresence>
    </motion.button>
  )
}
