/**
 * FeatureContributionList — ordered list of FeatureBar components
 * Documented Requirement: §5.4 "Top contributing features"
 * §8: "Feature contribution bars — Custom (SVG), bar length = magnitude, z-score label"
 * Bars are ordered by z_score descending (highest contribution first)
 */

import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'
import { FeatureBar } from './FeatureBar'
import type { ContributingFeature } from '@/types'

interface FeatureContributionListProps {
  features:  ContributingFeature[]
  className?: string
}

export const FeatureContributionList: React.FC<FeatureContributionListProps> = ({
  features,
  className,
}) => {
  const reduced = useReducedMotion()

  if (features.length === 0) {
    return (
      <p className="text-xs text-text-secondary italic py-2">
        No contributing features recorded for this entity.
      </p>
    )
  }

  // Sort by z_score descending (§5.4: ordered contribution bars)
  const sorted    = [...features].sort((a, b) => b.z_score - a.z_score)
  const maxZScore = sorted[0]?.z_score ?? 1

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {/* Section header */}
      <p className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider mb-2">
        Top contributing features
      </p>

      {/* §10: role="list" for screen reader enumeration */}
      <div role="list" aria-label="Contributing features ordered by impact">
        {sorted.map((f, idx) => (
          <motion.div
            key={f.feature}
            initial={reduced ? undefined : { opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              duration: reduced ? 0 : 0.25,
              delay:    reduced ? 0 : idx * 0.07,
              ease:     [0.2, 0, 0, 1],
            }}
            className="mb-3 last:mb-0"
          >
            <FeatureBar
              feature={f}
              maxZScore={maxZScore}
              index={idx}
            />
          </motion.div>
        ))}
      </div>
    </div>
  )
}
