/**
 * FeatureBar — §6 Component Library
 * Documented Requirement: §5.4 "Feature bars are horizontal, z-score labeled,
 * and directly hoverable to reveal the exact underlying transaction rows"
 * §8: "Bar length = magnitude, label = raw z-score, not just 'high/low'"
 *
 * Animations:
 * - Bar fill: scaleX from 0 → final on mount (§13: never animate width directly)
 * - Duration: motion-base 300ms (§7.1)
 * - Hover: tooltip with raw value + z-score context (§5.4 traceability)
 *
 * §10: hover state also keyboard-accessible via focus (focus-visible shows tooltip)
 * §10: z-score value always in accessibility tree
 */

import React, { useState, useId } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'
import { featureLabel, formatZScore } from '@/utils'
import type { ContributingFeature } from '@/types'

interface FeatureBarProps {
  feature:   ContributingFeature
  /** Max z-score in the set — used to scale bar width relatively */
  maxZScore: number
  /** Index for stagger delay */
  index?:    number
}

export const FeatureBar: React.FC<FeatureBarProps> = ({
  feature,
  maxZScore,
  index = 0,
}) => {
  const reduced    = useReducedMotion()
  const [hovered, setHovered] = useState(false)
  const [focused, setFocused] = useState(false)
  const tooltipId  = useId()

  // Bar fill fraction: z_score / maxZScore (clamped 0–1)
  const fraction = maxZScore > 0 ? Math.min(feature.z_score / maxZScore, 1) : 0

  // Color: high z-score (≥2) = amber, moderate = cyan, low = secondary
  const barColor =
    feature.z_score >= 2.5 ? 'bg-risk-high'
    : feature.z_score >= 1.5 ? 'bg-risk-medium'
    : 'bg-accent-cyan'

  const showTooltip = hovered || focused

  return (
    <div
      className="flex flex-col gap-1.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan rounded"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      tabIndex={0}
      role="listitem"
      aria-describedby={tooltipId}
      aria-label={`${featureLabel(feature.feature)}: value ${feature.value}, ${formatZScore(feature.z_score)}`}
    >
      {/* Row 1: Feature name + z-score label */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-text-secondary truncate max-w-[200px]" title={feature.feature}>
          {feature.feature}
        </span>
        <span className="text-[11px] font-mono text-text-secondary ml-2 shrink-0">
          {formatZScore(feature.z_score)}
        </span>
      </div>

      {/* Row 2: Bar + value */}
      <div className="flex items-center gap-2">
        {/* Value label */}
        <span className="text-xs font-mono text-text-primary w-8 text-right shrink-0">
          {feature.value}
        </span>

        {/* Bar track */}
        <div
          className="flex-1 h-1.5 rounded-full bg-border-hairline overflow-hidden relative"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={maxZScore}
          aria-valuenow={feature.z_score}
        >
          {/* Animated fill: scaleX only (§13) */}
          <motion.div
            className={cn('absolute inset-y-0 left-0 w-full rounded-full', barColor)}
            style={{ transformOrigin: 'left center' }}
            initial={{ scaleX: 0 }}
            animate={{ scaleX: fraction }}
            transition={{
              duration: reduced ? 0 : 0.3,
              delay: reduced ? 0 : index * 0.08,
              ease: [0.2, 0, 0, 1],
            }}
          />
        </div>

        {/* Hover indicator dot */}
        <span
          className={cn(
            'size-1.5 rounded-full shrink-0 transition-colors duration-[100ms]',
            showTooltip ? barColor : 'bg-border-hairline'
          )}
          aria-hidden
        />
      </div>

      {/* Hover tooltip — §5.4 "hoverable to reveal exact underlying transaction rows" */}
      {/* §10: always in accessibility tree via aria-describedby */}
      <span
        id={tooltipId}
        role="tooltip"
        className={cn(
          'text-[11px] text-text-secondary leading-snug',
          'transition-all duration-[100ms]',
          showTooltip ? 'opacity-100 max-h-12' : 'opacity-0 max-h-0 overflow-hidden',
          // sr-only fallback: even when hidden visually, SR can read it
          !showTooltip && 'sr-only',
        )}
        aria-live="polite"
      >
        Raw value: <span className="font-mono text-text-primary">{feature.value}</span>
        {' · '}z-score: <span className="font-mono text-text-primary">{feature.z_score.toFixed(2)}</span>
        {' · '}This feature contributed to the anomaly score based on deviation from cohort baseline.
      </span>
    </div>
  )
}
