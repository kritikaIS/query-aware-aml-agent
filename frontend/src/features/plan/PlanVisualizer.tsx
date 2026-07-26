/**
 * PlanVisualizer — Screen ② "Agent is Thinking"
 * Documented Requirement: §5.2 Live Execution Plan Visualizer
 *
 * Wireframe reproduced from §5.2:
 *  ┌─────────────────────────────────────────────────────────────────┐
 *  │ "Find structuring patterns in the last 30 days"                   │
 *  │                                                                   │
 *  │  ① Intent Parsed → pattern_detection · structuring               │
 *  │     filters: date_range = last 30d                               │
 *  │                                                                   │
 *  │  ② Building execution plan...  ▓▓▓▓▓▓▓▓░░  reasoning...          │
 *  │                                                                   │
 *  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐         │
 *  │  │DATA  │→│EDA   │ │FEAT  │→│DETECT│→│RISK  │→│EXPLAIN│         │
 *  │  │LOADER│ │SKIPPED│→│ENG. │ │(hyb) │ │CLASS.│ │(LLM) │         │
 *  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘         │
 *  │                                                                   │
 *  │  Agent Reasoning ▾  [typewriter text...]                         │
 *  │                                                                   │
 *  │                           [ Skip to Results → ]                  │
 *  └─────────────────────────────────────────────────────────────────┘
 *
 * Animations documented for this screen:
 * - §7.2 Seq 1: pipeline assembly (stagger, motion-slow 500ms, 60ms stagger)
 * - §7.2 Seq 2: skip reveal (250ms desaturation)
 * - §7.2 Seq 5: reasoning ticker typewriter
 * - §7.3: breathing pulse on planning indicator (ONE loop, 2.4s)
 * - §7.3: "skip to results" clickable at any point
 *
 * Responsive:
 * - Desktop: full pipeline row
 * - Tablet: horizontal scroll with snap points (via ToolPipeline)
 * - Mobile: vertical timeline (via ToolPipeline)
 */

import React from 'react'
import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { usePlannerStore, useQueryStore, useUiStore } from '@/stores'
import { useReducedMotion } from '@/hooks'
import {
  QuerySummary,
  PlanningIndicator,
  ToolPipeline,
  PlanReasoningTicker,
  ExecutionTimeline,
} from '@/components/aml'
import { cn } from '@/utils'
import { MOTION } from '@/constants'

export const PlanVisualizer: React.FC = () => {
  // ── Mock driver removed: stores are now driven by useQuery in QueryConsole ──
  // useMockPlanDriver() replaced by real backend SSE events via useQuery hook.
  // The plannerStore is populated by synthetic SSE events fired from connectSse()
  // in response to the real POST /query backend response.

  const reduced = useReducedMotion()

  // ── Read from stores (§12 data flow) ───────────────────────────────
  const toolCards      = usePlannerStore((s) => s.toolCards)
  const querySpec      = usePlannerStore((s) => s.querySpec)
  const reasoningText  = usePlannerStore((s) => s.reasoningText)
  const isPlanning     = usePlannerStore((s) => s.isPlanning)
  const submittedQuery = useQueryStore((s)  => s.submittedQuery)
  const queryStatus    = useQueryStore((s)  => s.status)

  const setView    = useUiStore((s) => s.setView)

  const isPlanComplete = queryStatus === 'complete'

  // ── Page entrance ──────────────────────────────────────────────────
  const sectionVariants = {
    hidden:  { opacity: 0, y: reduced ? 0 : 16 },
    visible: {
      opacity: 1, y: 0,
      transition: { duration: reduced ? 0 : MOTION.BASE, ease: [0.2, 0, 0, 1] as [number,number,number,number] },
    },
  }

  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: reduced ? 0 : 0.08,
        delayChildren: 0,
      },
    },
  }

  return (
    // Fix #16: removed duplicate role="main" — AppShell already provides <main>
    <div className="flex-1 flex flex-col px-4 tablet:px-6 desktop:px-8 py-6 desktop:py-8 gap-6">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="w-full max-w-[1200px] mx-auto flex flex-col gap-6"
      >

        {/* ── ① Query + Intent Summary ── */}
        <motion.div variants={sectionVariants}>
          <QuerySummary
            query={submittedQuery ?? ''}
            querySpec={querySpec}
            parsing={!querySpec && isPlanning}
          />
        </motion.div>

        {/* ── ② Building Execution Plan indicator ── */}
        <motion.div variants={sectionVariants}>
          <PlanningIndicator
            isPlanning={isPlanning}
            toolCount={toolCards.length}
            totalTools={6}
          />
        </motion.div>

        {/* ── Tool Pipeline (§5.2, §7.2 Seq 1+2) ── */}
        {toolCards.length > 0 && (
          <motion.div
            variants={sectionVariants}
            role="region"
            aria-label="Tool execution pipeline"
          >
            <div className="flex flex-col gap-3">
              {/* Section label */}
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
                  Execution Pipeline
                </span>
                <span className="text-[11px] font-mono text-text-secondary">
                  ({toolCards.filter(c => c.state !== 'skipped').length} active ·{' '}
                  {toolCards.filter(c => c.state === 'skipped').length} skipped)
                </span>
              </div>

              {/* The pipeline — dynamically assembled, never hardcoded */}
              <ToolPipeline cards={toolCards} />
            </div>
          </motion.div>
        )}

        {/* ── Execution timeline summary (shown after plan_complete) ── */}
        <ExecutionTimeline
          cards={toolCards}
          visible={isPlanComplete}
        />

        {/* ── Reasoning Ticker (§5.2, §7.2 Seq 5) ── */}
        {reasoningText.length > 0 && (
          <motion.div variants={sectionVariants}>
            <PlanReasoningTicker
              text={reasoningText}
              isStreaming={isPlanning}
            />
          </motion.div>
        )}

        {/* ── Skip to Results (§7.3: judge can click at any point) ── */}
        <motion.div
          variants={sectionVariants}
          className="flex justify-end pt-2"
        >
          <button
            type="button"
            onClick={() => setView('results')}
            className={cn(
              'inline-flex items-center gap-2 h-9 px-4',
              'rounded-lg text-sm font-medium',
              isPlanComplete
                // After plan complete: primary cyan — "proceed to results"
                ? 'bg-accent-cyan text-bg-void hover:opacity-90'
                // During planning: ghost — available but not pushing
                : 'bg-transparent text-text-secondary border border-border-hairline hover:text-text-primary hover:border-accent-cyan/40',
              'transition-all duration-[180ms] ease-[cubic-bezier(0.2,0,0,1)]',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-void',
              'cursor-pointer'
            )}
            aria-label={isPlanComplete ? 'View results dashboard' : 'Skip to results (plan still in progress)'}
          >
            {isPlanComplete ? 'View Results' : 'Skip to Results'}
            <ArrowRight size={14} aria-hidden />
          </button>
        </motion.div>

      </motion.div>
    </div>
  )
}
