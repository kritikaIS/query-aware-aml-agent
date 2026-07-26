/**
 * KpiTile — §6 Component Library
 * States: loading · counted-up
 * Documented Requirement: §7.2 Seq 4 "ease-out count from 0 → final value over
 * 600ms, only on first mount, never on re-render"
 * §5.3: "KPI tiles count up from 0 on entry — the only place counting-up animation is used"
 * §13: chart entrance motion-slow 500ms
 */

import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/utils'
import { useCountUp } from '@/hooks'
import { formatCount } from '@/utils'
import { MOTION } from '@/constants'

interface KpiTileProps {
  value:       number
  label:       string
  sublabel?:   string
  /** Optional right-side content (e.g. mini donut) */
  aside?:      React.ReactNode
  loading?:    boolean
  className?:  string
  valueClass?: string
}

export const KpiTile: React.FC<KpiTileProps> = ({
  value,
  label,
  sublabel,
  aside,
  loading = false,
  className,
  valueClass,
}) => {
  // Fix #40: removed redundant useReducedMotion() — Framer Motion's motion.div
  // respects prefers-reduced-motion automatically via its own internal hook.
  const animatedVal = useCountUp(value)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: MOTION.SLOW, ease: 'easeInOut' }}
      className={cn(
        'panel flex flex-col justify-between gap-2',
        'min-h-[100px] p-5',
        className
      )}
      role="region"
      aria-label={`${label}: ${formatCount(value)}`}
    >
      <div className="flex items-start justify-between gap-2">
        {/* ── Main value (count-up, §7.2 Seq 4) ── */}
        <div className="flex flex-col gap-0.5">
          {loading ? (
            <div className="h-9 w-24 rounded bg-bg-panel-raised animate-pulse" aria-hidden />
          ) : (
            <span
              className={cn(
                'text-3xl font-bold font-mono text-text-primary leading-none',
                valueClass
              )}
              aria-live="off"   // value announced via aria-label on container
            >
              {formatCount(animatedVal)}
            </span>
          )}
          <span className="text-xs font-medium text-text-secondary uppercase tracking-wider mt-1">
            {label}
          </span>
          {sublabel && (
            <span className="text-[11px] text-text-secondary">{sublabel}</span>
          )}
        </div>

        {/* Optional right-side content (donut, etc.) */}
        {aside && (
          <div className="shrink-0">{aside}</div>
        )}
      </div>
    </motion.div>
  )
}
