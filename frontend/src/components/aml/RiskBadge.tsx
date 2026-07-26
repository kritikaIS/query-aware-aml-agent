/**
 * RiskBadge — §6 Component Library
 * States: low · medium · high
 * Documented Requirement: "Color + icon, never color alone (see §10)"
 * §7.2 Seq 3: resolves via 400ms animation on mount (score-resolve)
 * §10: color + icon + text label always present
 */

import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'
import type { RiskBand } from '@/types'

interface RiskBadgeProps {
  band:       RiskBand
  /** When true, runs the 400ms score-resolve animation (§7.2 Seq 3) */
  animate?:   boolean
  size?:      'sm' | 'md' | 'lg'
  className?: string
}

const BAND_CONFIG: Record<RiskBand, {
  label: string
  icon:  string
  textClass:   string
  bgClass:     string
  borderClass: string
}> = {
  High: {
    label:       'High',
    icon:        '●',
    textClass:   'text-risk-high',
    bgClass:     'bg-risk-high/10',
    borderClass: 'border-risk-high/40',
  },
  Medium: {
    label:       'Med',
    icon:        '●',
    textClass:   'text-risk-medium',
    bgClass:     'bg-risk-medium/10',
    borderClass: 'border-risk-medium/40',
  },
  Low: {
    label:       'Low',
    icon:        '●',
    textClass:   'text-risk-low',
    bgClass:     'bg-risk-low/10',
    borderClass: 'border-risk-low/40',
  },
}

const SIZE_CLASS = {
  sm: 'text-[10px] px-1.5 py-0.5 gap-1',
  md: 'text-xs    px-2   py-0.5 gap-1',
  lg: 'text-sm    px-2.5 py-1   gap-1.5',
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  band,
  animate = false,
  size = 'md',
  className,
}) => {
  const reduced = useReducedMotion()
  const cfg     = BAND_CONFIG[band]

  return (
    // §7.2 Seq 3: 400ms scale+opacity resolve; only on first render of badge
    <motion.span
      initial={animate && !reduced ? { opacity: 0, scale: 0.7 } : { opacity: 1, scale: 1 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={animate && !reduced ? { duration: 0.4, ease: [0.2, 0, 0, 1] } : { duration: 0 }}
      className={cn(
        'inline-flex items-center font-mono font-semibold rounded-full border',
        cfg.textClass,
        cfg.bgClass,
        cfg.borderClass,
        SIZE_CLASS[size],
        className,
      )}
      aria-label={`Risk level: ${band}`}
    >
      {/* Icon — §10: never color alone */}
      <span aria-hidden className="text-[8px]">{cfg.icon}</span>
      {/* Text label */}
      <span>{cfg.label}</span>
    </motion.span>
  )
}
