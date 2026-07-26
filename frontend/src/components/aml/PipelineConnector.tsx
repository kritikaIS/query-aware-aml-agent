/**
 * PipelineConnector — arrow between two active tool cards
 * Documented Requirement: §8 "edges only drawn between tools that actually
 * ran in sequence" — connectors between active (non-skipped) tool pairs only.
 *
 * §13: SVG/transform only — no layout-thrashing properties
 */

import React from 'react'
import { motion } from 'framer-motion'
import { useReducedMotion } from '@/hooks'

interface PipelineConnectorProps {
  /** Whether both adjacent tools are active (non-skipped) */
  active: boolean
}

export const PipelineConnector: React.FC<PipelineConnectorProps> = ({ active }) => {
  const reduced = useReducedMotion()

  if (!active) {
    // Skipped connector: dashed, dimmed
    return (
      <div
        className="shrink-0 flex items-center justify-center w-5 self-center mt-2"
        aria-hidden
      >
        <svg width="20" height="2" viewBox="0 0 20 2">
          <line
            x1="0" y1="1" x2="20" y2="1"
            stroke="var(--skipped-grey)"
            strokeWidth="1"
            strokeDasharray="3 2"
          />
        </svg>
      </div>
    )
  }

  return (
    <div
      className="shrink-0 flex items-center justify-center w-5 self-center mt-2"
      aria-hidden
    >
      <svg width="20" height="10" viewBox="0 0 20 10">
        {/* Connector line */}
        <motion.line
          x1="0" y1="5" x2="14" y2="5"
          stroke="var(--accent-cyan)"
          strokeWidth="1"
          strokeOpacity="0.5"
          initial={reduced ? undefined : { pathLength: 0 }}
          animate={reduced ? undefined : { pathLength: 1 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.1 }}
        />
        {/* Arrowhead */}
        <motion.polyline
          points="11,2 16,5 11,8"
          fill="none"
          stroke="var(--accent-cyan)"
          strokeWidth="1"
          strokeOpacity="0.5"
          initial={reduced ? undefined : { opacity: 0 }}
          animate={reduced ? undefined : { opacity: 1 }}
          transition={{ duration: 0.15, delay: 0.35 }}
        />
      </svg>
    </div>
  )
}
