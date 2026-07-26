/**
 * ToolPipeline — the dynamic, ordered pipeline of ToolCards
 * Documented Requirement: §5.2
 * - Left-to-right pipeline, dynamically assembled
 * - Cards appear in execution order (stagger left-to-right)
 * - Never hardcodes tool positions
 * - Connectors only between active (non-skipped) pairs (§8)
 *
 * §7.2 Seq 1: stagger container — cards fade+slide up, motion-slow 500ms, 60ms stagger
 * §9 Responsive:
 *   - Desktop: full horizontal row
 *   - Tablet: horizontally scrollable with snap points
 *   - Mobile: vertical timeline (collapses, §9)
 */

import React from 'react'
import { motion } from 'framer-motion'
import { ToolCard } from './ToolCard'
import { PipelineConnector } from './PipelineConnector'
import { useReducedMotion } from '@/hooks'
import { MOTION } from '@/constants'
import type { ToolCardModel } from '@/types'

// LLM tools get violet accent (§4.1)
const LLM_TOOLS = new Set(['explanation'])

interface ToolPipelineProps {
  cards: ToolCardModel[]
}

export const ToolPipeline: React.FC<ToolPipelineProps> = ({ cards }) => {
  const reduced = useReducedMotion()

  if (cards.length === 0) return null

  // ── Stagger container (§7.2 Seq 1) ─────────────────────────────────
  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: reduced ? 0 : MOTION.STAGGER_DELAY,
        delayChildren:   0,
      },
    },
  }

  // ── Individual card slide-up (§7.2 Seq 1: motion-slow 500ms) ───────
  const cardVariants = {
    hidden:  { opacity: 0, y: reduced ? 0 : 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: reduced ? 0 : MOTION.SLOW,
        ease: [0.2, 0, 0, 1] as [number, number, number, number],
      },
    },
  }

  return (
    <>
      {/* ─── Desktop + Tablet: horizontal pipeline ─── */}
      <div className="hidden mobile:block">
        {/* Tablet: horizontally scrollable with snap points (§9) */}
        <div className="tablet:overflow-x-auto tablet:snap-x tablet:snap-mandatory desktop:overflow-visible">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="flex items-start gap-0 min-w-max desktop:min-w-0 desktop:flex-wrap"
            role="list"
            aria-label="Execution pipeline tools"
          >
            {cards.map((card, idx) => {
              const isLast      = idx === cards.length - 1
              const nextCard    = cards[idx + 1]
              // Connector is active only if both this and next are NOT skipped (§8)
              const connActive  = !isLast
                && card.state !== 'skipped'
                && nextCard?.state !== 'skipped'

              return (
                <React.Fragment key={card.name}>
                  <motion.div
                    variants={cardVariants}
                    className="tablet:snap-start"
                    role="listitem"
                  >
                    <ToolCard
                      name={card.name}
                      label={card.label}
                      state={card.state}
                      progress={card.progress}
                      skipReason={card.skipReason}
                      isLlm={LLM_TOOLS.has(card.name)}
                    />
                  </motion.div>

                  {/* Connector between cards (§8) */}
                  {!isLast && (
                    <motion.div
                      variants={cardVariants}
                      className="self-center mt-2"
                    >
                      <PipelineConnector active={connActive} />
                    </motion.div>
                  )}
                </React.Fragment>
              )
            })}
          </motion.div>
        </div>
      </div>

      {/* ─── Mobile: vertical timeline (§9) ─── */}
      <div className="block mobile:hidden">
        <motion.ol
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col gap-0"
          aria-label="Execution pipeline tools"
        >
          {cards.map((card, idx) => {
            const isLast   = idx === cards.length - 1
            const nextCard = cards[idx + 1]
            const connActive = !isLast
              && card.state !== 'skipped'
              && nextCard?.state !== 'skipped'

            return (
              <motion.li key={card.name} variants={cardVariants} className="flex flex-col items-start">
                {/* Full-width card on mobile */}
                <div className="w-full">
                  <ToolCard
                    name={card.name}
                    label={card.label}
                    state={card.state}
                    progress={card.progress}
                    skipReason={card.skipReason}
                    isLlm={LLM_TOOLS.has(card.name)}
                  />
                </div>
                {/* Vertical connector */}
                {!isLast && (
                  <div className="ml-6 my-1" aria-hidden>
                    <svg width="2" height="20" viewBox="0 0 2 20">
                      <line
                        x1="1" y1="0" x2="1" y2="20"
                        stroke={connActive ? 'var(--accent-cyan)' : 'var(--skipped-grey)'}
                        strokeWidth="1"
                        strokeOpacity="0.4"
                        strokeDasharray={connActive ? undefined : '3 2'}
                      />
                    </svg>
                  </div>
                )}
              </motion.li>
            )
          })}
        </motion.ol>
      </div>
    </>
  )
}
