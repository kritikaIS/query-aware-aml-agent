/**
 * PlanReasoningTicker — §6 Component Library
 * States: streaming · complete
 * Documented Requirements:
 * - §5.2: "collapsible 'Agent reasoning' ticker beneath the header"
 * - §5.2: "streams the planner's reasoning string token-by-token, typewriter-style"
 * - §5.2: "the ONLY place a typewriter effect is used" — deliberate, not gimmicky
 * - §7.1: motion-stream 20–35ms/char, linear
 * - §7.2 Seq 5: skippable on click (jumps to full text)
 * - §7.3: prefers-reduced-motion → instant full text
 * - §10: aria-live="polite" region so screen readers announce streaming text
 * - §4.1: accent-violet for LLM/planning-related elements
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronRight, Zap } from 'lucide-react'
import { cn } from '@/utils'
import { useTypewriter } from '@/hooks'

interface PlanReasoningTickerProps {
  text:        string
  isStreaming: boolean   // true while plan is still being built
}

export const PlanReasoningTicker: React.FC<PlanReasoningTickerProps> = ({
  text,
  isStreaming,
}) => {
  const [collapsed, setCollapsed] = useState(false)

  // §7.2 Seq 5: typewriter effect, skippable on click
  const { displayed, isComplete, skip } = useTypewriter({
    text,
    onComplete: undefined,
  })

  const toggleCollapse = () => setCollapsed((c) => !c)

  return (
    <div className="panel rounded-lg overflow-hidden">
      {/* ── Header row: collapsible toggle + label ── */}
      <button
        type="button"
        onClick={toggleCollapse}
        className={cn(
          'w-full flex items-center gap-2 px-4 py-3',
          'text-left',
          'hover:bg-bg-panel-raised transition-colors duration-[100ms]',
          'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan',
        )}
        aria-expanded={!collapsed}
        aria-controls="reasoning-ticker-body"
      >
        {/* Violet accent — §4.1 LLM/planning elements */}
        <Zap size={13} className="text-accent-violet shrink-0" aria-hidden />
        <span className="text-xs font-semibold text-accent-violet uppercase tracking-wider">
          Agent Reasoning
        </span>
        {isStreaming && (
          <span className="ml-1 text-[10px] font-mono text-accent-cyan animate-pulse">
            streaming…
          </span>
        )}
        {/* Collapse/expand chevron — right-aligned */}
        <span className="ml-auto text-text-secondary">
          {collapsed
            ? <ChevronRight size={13} aria-hidden />
            : <ChevronDown  size={13} aria-hidden />
          }
        </span>
      </button>

      {/* ── Ticker body (collapsible) ── */}
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            id="reasoning-ticker-body"
            key="ticker-body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1, transition: { duration: 0.25, ease: [0.2, 0, 0, 1] } }}
            exit={{   height: 0, opacity: 0, transition: { duration: 0.2,  ease: 'easeInOut' } }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-1">
              {/* §10: aria-live="polite" announces streaming text to screen readers */}
              <p
                aria-live="polite"
                aria-atomic="false"
                className={cn(
                  'text-sm text-text-secondary leading-relaxed',
                  // Typewriter cursor while streaming
                  !isComplete && isStreaming && 'after:content-["▋"] after:text-accent-cyan after:animate-pulse after:ml-0.5'
                )}
              >
                {displayed}
                {/* Hidden full text for screen readers when typewriter is active */}
                {!isComplete && (
                  <span className="sr-only">{text}</span>
                )}
              </p>

              {/* Skip button (§7.2 Seq 5: skippable on click) */}
              {!isComplete && text.length > 0 && (
                <button
                  type="button"
                  onClick={skip}
                  className={cn(
                    'mt-2 text-[11px] text-text-secondary hover:text-accent-cyan',
                    'underline underline-offset-2 cursor-pointer',
                    'transition-colors duration-[100ms]',
                    'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan rounded'
                  )}
                  aria-label="Skip typewriter animation and show full reasoning text"
                >
                  Skip animation
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
