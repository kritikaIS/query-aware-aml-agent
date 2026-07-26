/**
 * MetricsRail — chart section of the Results Dashboard
 * Documented Requirement: §5.3 wireframe bottom row:
 *   ┌──────────────────────┐  ┌───────────────────────────┐
 *   │ Amount distribution   │  │ Flagged activity timeline  │
 *   │  (histogram + $10k    │  │  (scatter, near-threshold  │
 *   │   threshold line)     │  │   clusters highlighted)    │
 *   └──────────────────────┘  └───────────────────────────┘
 *
 * §9 Responsive: "charts stack to single column" on tablet
 * §7.1 motion-slow 500ms chart entrance
 */

import React from 'react'
import { motion } from 'framer-motion'
import { ThresholdHistogram } from '@/components/aml'
import { TimelineScatter } from '@/components/aml'
import { useReducedMotion } from '@/hooks'
import { MOTION } from '@/constants'
import type { HistogramBin, TimelinePoint } from './types'

interface MetricsRailProps {
  histogramData: HistogramBin[]
  timelineData:  TimelinePoint[]
}

export const MetricsRail: React.FC<MetricsRailProps> = ({
  histogramData,
  timelineData,
}) => {
  const reduced = useReducedMotion()

  const chartVariants = {
    hidden:  { opacity: 0, y: reduced ? 0 : 20 },
    visible: (i: number) => ({
      opacity: 1, y: 0,
      transition: {
        duration: reduced ? 0 : MOTION.SLOW,
        ease: 'easeInOut',
        delay: reduced ? 0 : i * 0.1,
      },
    }),
  }

  return (
    // §9: Desktop: 2-column grid. Tablet: single column.
    <div className="grid grid-cols-1 tablet:grid-cols-2 gap-6">

      {/* Left: Amount distribution histogram (§8) */}
      <motion.div
        custom={0}
        variants={chartVariants}
        initial="hidden"
        animate="visible"
        className="panel p-4"
      >
        <div className="mb-3">
          <h3 className="text-xs font-semibold text-text-primary">
            Amount Distribution
          </h3>
          <p className="text-[11px] text-text-secondary mt-0.5">
            Clustering just under the $10,000 reporting threshold
          </p>
        </div>
        <ThresholdHistogram data={histogramData} />
      </motion.div>

      {/* Right: Flagged activity timeline scatter (§8) */}
      <motion.div
        custom={1}
        variants={chartVariants}
        initial="hidden"
        animate="visible"
        className="panel p-4"
      >
        <div className="mb-3">
          <h3 className="text-xs font-semibold text-text-primary">
            Flagged Activity Timeline
          </h3>
          <p className="text-[11px] text-text-secondary mt-0.5">
            Point size = amount · <span className="text-risk-high">●</span> near-threshold
            &nbsp;· <span className="text-risk-medium">●</span> flagged
            &nbsp;· <span className="text-accent-cyan">●</span> normal
          </p>
        </div>
        <TimelineScatter data={timelineData} />
      </motion.div>

    </div>
  )
}
