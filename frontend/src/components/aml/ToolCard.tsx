/**
 * ToolCard — §6 Component Library
 * States: queued · running · done · skipped · error
 *
 * Documented Requirements:
 * - Skipped state always shows reason text, NO hover required (§6)
 * - Skipped card: grey, strikethrough label, skip-reason visible (§5.2)
 * - Active card: live progress bar + status chip queued→running→done (§5.2)
 * - §7.2 Seq 1: cards fade+slide up (motion-slow 500ms, stagger via parent)
 * - §7.2 Seq 2: skip reveal — briefly full color → desaturates+strikes 250ms
 * - §4.1: skipped uses --skipped-grey; active uses --accent-cyan
 * - §10: skip-reason ALWAYS in accessibility tree (not just visual tooltip)
 * - §10: color never only signal — status icon + text label on every state
 */

import React, { useEffect, useRef } from 'react'
import { motion, useAnimation } from 'framer-motion'
import { CheckCircle2, Circle, Loader2, XCircle, AlertCircle } from 'lucide-react'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'
import type { ToolState } from '@/types'
import { ToolProgressBar } from './ToolProgressBar'
import { ToolStatusBadge } from './ToolStatusBadge'

interface ToolCardProps {
  name:        string    // tool registry key
  label:       string    // human-readable label
  state:       ToolState
  progress:    number    // 0–100
  skipReason?: string    // populated when state === 'skipped'
  /** Whether this card is an LLM/reasoning tool (violet accent §4.1) */
  isLlm?:      boolean
}

// ── State → icon mapping (§10: color never only signal) ──────────────
const STATE_ICON: Record<ToolState, React.ReactNode> = {
  queued:  <Circle       size={14} className="text-text-secondary" aria-hidden />,
  running: <Loader2      size={14} className="text-accent-cyan animate-spin" aria-hidden />,
  done:    <CheckCircle2 size={14} className="text-risk-low" aria-hidden />,
  skipped: <XCircle      size={14} className="text-skipped" aria-hidden />,
  error:   <AlertCircle  size={14} className="text-risk-high" aria-hidden />,
}

// ── State → aria label suffix ─────────────────────────────────────────
const STATE_ARIA: Record<ToolState, string> = {
  queued:  'queued',
  running: 'running',
  done:    'completed',
  skipped: 'skipped',
  error:   'error',
}

export const ToolCard: React.FC<ToolCardProps> = ({
  name,
  label,
  state,
  progress,
  skipReason,
  isLlm = false,
}) => {
  const reduced  = useReducedMotion()
  const controls = useAnimation()
  const prevStateRef = useRef<ToolState | null>(null)

  // ── §7.2 Seq 2: Skip reveal animation ─────────────────────────────
  // Card briefly appears in full color, then desaturates + strikes through over 250ms
  useEffect(() => {
    const prev = prevStateRef.current
    prevStateRef.current = state

    if (state === 'skipped' && prev !== 'skipped' && !reduced) {
      // Phase 1: show at full color (0ms)
      controls.start({ filter: 'saturate(1)', opacity: 1 })
      // Phase 2: desaturate + fade to skipped final state (250ms §7.2)
      setTimeout(() => {
        controls.start({
          filter:  'saturate(0)',
          opacity: 0.6,
          transition: { duration: 0.25, ease: 'easeInOut' },
        })
      }, 80) // brief moment at full color so judge perceives "was considered"
    }
  }, [state, controls, reduced])

  const isSkipped = state === 'skipped'
  const isDone    = state === 'done'
  const isRunning = state === 'running'
  const isError   = state === 'error'

  // ── Card surface styles per state ────────────────────────────────────
  const cardBg = isSkipped
    ? 'bg-bg-panel border-skipped/40'
    : isError
      ? 'bg-bg-panel border-risk-high/40'
      : isDone
        ? 'bg-bg-panel border-risk-low/30'
        : isRunning
          ? 'bg-bg-panel-raised border-accent-cyan/40'
          : 'bg-bg-panel border-border-hairline' // queued

  // LLM tools get violet accent per §4.1
  const accentColor = isLlm ? 'text-accent-violet' : 'text-accent-cyan'

  return (
    // Stagger animation is applied by parent ToolPipeline (§7.2 seq 1)
    <motion.article
      animate={isSkipped && !reduced ? controls : undefined}
      // Initial filter state for skip reveal
      initial={isSkipped && !reduced ? { filter: 'saturate(1)', opacity: 1 } : undefined}
      aria-label={`Tool: ${label} (${name}), status: ${STATE_ARIA[state]}${skipReason ? `. Skip reason: ${skipReason}` : ''}`}
      tabIndex={0}
      className={cn(
        // Base card geometry
        'relative flex flex-col gap-2 p-4 rounded-lg border',
        'min-w-[148px] w-[148px] shrink-0',
        // State-driven surface
        cardBg,
        // Transition for state changes: motion-fast (§7.1)
        'transition-all duration-[180ms] ease-[cubic-bezier(0.2,0,0,1)]',
        // Focus ring: §10 keyboard accessible
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-cyan focus-visible:ring-offset-1 focus-visible:ring-offset-bg-void',
        // Running state: subtle top accent bar
        isRunning && 'shadow-[0_0_0_1px_rgba(62,214,196,0.2),inset_0_1px_0_rgba(62,214,196,0.15)]',
      )}
    >
      {/* ── Top row: icon + status badge ── */}
      <div className="flex items-center justify-between gap-1">
        <span className="shrink-0">
          {STATE_ICON[state]}
        </span>
        <ToolStatusBadge state={state} />
      </div>

      {/* ── Tool label ── */}
      {/* §5.2: skipped tools have strikethrough label */}
      <div className={cn(
        'text-xs font-semibold tracking-wide uppercase',
        isSkipped
          ? 'line-through text-text-secondary decoration-skipped decoration-1'
          : isLlm
            ? accentColor
            : isDone
              ? 'text-risk-low'
              : isRunning
                ? 'text-accent-cyan'
                : 'text-text-secondary'
      )}>
        {label}
      </div>

      {/* ── Progress bar (running/done states) ── */}
      {!isSkipped && (
        <ToolProgressBar
          progress={progress}
          state={state}
          isLlm={isLlm}
        />
      )}

      {/* ── Skip reason — §6: always visible, no hover required ── */}
      {/* §10: always in accessibility tree even when visually shown as text */}
      {isSkipped && skipReason && (
        <p
          className="text-[11px] text-text-secondary leading-snug mt-0.5"
          // §10: skip-reason text always in accessibility tree
          aria-label={`Skip reason: ${skipReason}`}
        >
          {skipReason}
        </p>
      )}

      {/* ── LLM badge for explanation tool ── */}
      {isLlm && !isSkipped && (
        <span className="absolute -top-1.5 -right-1.5 text-[9px] font-mono font-medium px-1.5 py-0.5 rounded-full bg-accent-violet/20 text-accent-violet border border-accent-violet/30">
          LLM
        </span>
      )}

      {/* ── Running: active indicator dot (breathing pulse via CSS) ── */}
      {isRunning && (
        <span
          className="absolute top-2 right-2 size-1.5 rounded-full bg-accent-cyan animate-pulse"
          aria-hidden
        />
      )}
    </motion.article>
  )
}
