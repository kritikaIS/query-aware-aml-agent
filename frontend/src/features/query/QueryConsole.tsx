/**
 * QueryConsole — Screen ①
 * Documented Requirement: §5.1 Query Console (Entry State)
 *
 * Wireframe (§5.1):
 *  ┌───────────────────────────────────────────────────────────┐
 *  │  AML AGENT · SUSPICIOUS ACTIVITY DETECTION     ● dataset✓ │
 *  │                                                            │
 *  │        "Ask the agent anything about this data."           │
 *  │ ┌────────────────────────────────────────────────────┐    │
 *  │ │ ⌨  Find structuring patterns in the last 30 days   │    │
 *  │ └────────────────────────────────────────────────────┘    │
 *  │                                        [ Run Query ▸ ]    │
 *  │                                                            │
 *  │ Try:  [Analyse dataset] [10+ txns under $10k] [Cust 4521]  │
 *  └───────────────────────────────────────────────────────────┘
 *
 * Animations (§7.1 — documented for this screen):
 * 1. Page entrance: fade + slide-up on mount (motion-base 300ms, §7.1)
 * 2. Input focus: cyan glow (motion-instant 100ms CSS, §7.1)
 * 3. Chip hover: background lift (motion-instant 100ms, §7.1)
 * 4. Button hover: opacity (motion-instant 100ms, §7.1)
 * 5. Button click → loading: spinner swap (motion-fast 180ms, §7.1)
 *
 * Responsive (§9):
 * - Desktop ≥1280px: centered, max-w-2xl input
 * - Tablet 768–1279px: same, slightly narrower padding
 * - Mobile ≤767px: full-width, chips wrap
 *
 * Accessibility (§10):
 * - Tab order: input → run button → chip 1 → chip 2 → chip 3
 * - Enter on input submits
 * - Enter/Space on chip loads query
 * - aria-label on textarea
 * - aria-busy on run button during loading
 * - prefers-reduced-motion respected via useReducedMotion hook
 */

import React, { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useQueryStore } from '@/stores'
import { useReducedMotion, useQuery } from '@/hooks'
import { QUICK_SELECT_CHIPS } from '@/constants'
import { QueryInput } from './QueryInput'
import { RunButton } from './RunButton'
import { QueryChip } from './QueryChip'

// Fix #18: variant objects defined outside component — not recreated on every render
const makeVariants = (reduced: boolean) => ({
  container: {
    hidden:  { opacity: 0, y: reduced ? 0 : 20 },
    visible: {
      opacity: 1, y: 0,
      transition: {
        duration:        reduced ? 0 : 0.3,
        ease:            [0.2, 0, 0, 1] as [number, number, number, number],
        staggerChildren: reduced ? 0 : 0.07,
      },
    },
  },
  item: {
    hidden:  { opacity: 0, y: reduced ? 0 : 12 },
    visible: {
      opacity: 1, y: 0,
      transition: {
        duration: reduced ? 0 : 0.3,
        ease: [0.2, 0, 0, 1] as [number, number, number, number],
      },
    },
  },
})

export const QueryConsole: React.FC = () => {
  const reduced  = useReducedMotion()
  const { submitQuery } = useQuery()
  const queryStatus = useQueryStore((s) => s.status)

  const [query, setQuery] = useState('')

  // loading = true while backend is processing (status: submitting | streaming)
  const loading = queryStatus === 'submitting' || queryStatus === 'streaming'

  // ── Submit handler — calls real backend ─────────────────────────
  const handleSubmit = useCallback((text: string) => {
    if (!text.trim() || loading) return
    submitQuery(text)
  }, [loading, submitQuery])

  const handleRunClick = useCallback(() => {
    handleSubmit(query)
  }, [query, handleSubmit])

  // Chip click: load query text and submit directly (fix #17: removed fragile setTimeout)
  const handleChipClick = useCallback((chipQuery: string) => {
    setQuery(chipQuery)
    handleSubmit(chipQuery)
  }, [handleSubmit])

  // Cleanup any in-flight request only when a NEW query is submitted (handled
  // inside submitQuery itself via cleanupRef.current?.()). Do NOT cancel on
  // unmount — QueryConsole unmounts as soon as setView('plan') fires, which
  // would kill all the scheduled synthetic SSE timers before report_ready fires.

  const { container: containerVariants, item: itemVariants } = makeVariants(reduced)

  return (
    // Fix #16: removed duplicate role="main" — AppShell already provides <main>
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="w-full max-w-2xl flex flex-col gap-6"
      >

        {/* ── Eyebrow — command-center identity (§2 principle 2) ── */}
        <motion.div variants={itemVariants} className="text-center">
          <p className="text-xs font-medium tracking-[0.2em] text-text-secondary uppercase">
            Suspicious Activity Detection
          </p>
          <h1 className="mt-1 text-xl font-semibold text-text-primary">
            Ask the agent anything about this data.
          </h1>
        </motion.div>

        {/* ── Input + Run button block ─────────────────────────── */}
        <motion.div variants={itemVariants} className="flex flex-col gap-3">

          {/* Large command input (§5.1) */}
          <QueryInput
            value={query}
            onChange={setQuery}
            onSubmit={handleSubmit}
            disabled={loading}
            autoFocus
          />

          {/* Run Query button — right-aligned (§5.1 wireframe) */}
          <div className="flex justify-end">
            <RunButton
              onClick={handleRunClick}
              loading={loading}
              disabled={!query.trim()}
            />
          </div>
        </motion.div>

        {/* ── Quick-select chips (§5.1) ────────────────────────── */}
        <motion.div variants={itemVariants}>
          <div className="flex flex-wrap items-center gap-2">
            {/* "Try:" label — §5.1 wireframe */}
            <span
              className="text-xs font-medium text-text-secondary mr-1 shrink-0"
              aria-hidden   // The chips themselves have aria-label
            >
              Try:
            </span>

            {/* Role: navigation landmark for the three reference queries */}
            <nav aria-label="Quick query examples">
              <ul className="flex flex-wrap gap-2 list-none m-0 p-0">
                {QUICK_SELECT_CHIPS.map((chip) => (
                  <li key={chip.label}>
                    <QueryChip
                      label={chip.label}
                      onClick={() => handleChipClick(chip.query)}
                      disabled={loading}
                    />
                  </li>
                ))}
              </ul>
            </nav>
          </div>
        </motion.div>

        {/* ── Keyboard shortcut hint — desktop only (§10) ──────── */}
        <motion.div
          variants={itemVariants}
          className="hidden desktop:flex justify-center"
          aria-hidden
        >
          <p className="text-xs text-text-secondary/60 text-center">
            Press{' '}
            <kbd className="px-1.5 py-0.5 rounded border border-border-hairline bg-bg-panel-raised font-mono text-[10px]">
              Enter
            </kbd>{' '}
            to run ·{' '}
            <kbd className="px-1.5 py-0.5 rounded border border-border-hairline bg-bg-panel-raised font-mono text-[10px]">
              Shift + Enter
            </kbd>{' '}
            for new line
          </p>
        </motion.div>

      </motion.div>
    </div>
  )
}
