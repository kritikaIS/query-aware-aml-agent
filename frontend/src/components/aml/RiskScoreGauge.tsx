/**
 * RiskScoreGauge — animated risk score display
 * Documented Requirement: §5.4 "🔴 HIGH · score 0.87"
 * §7.2 Seq 3: score-resolve animation — 400ms circular sweep before snapping to color
 * §4.1: risk colors are the only saturated signal colors
 * §4.2: score is a monospace value (machine-generated)
 * §10: color never only signal — always has text label
 *
 * Implemented as an SVG arc gauge that sweeps from 0 to the risk score over 400ms.
 */

import React, { useEffect, useState } from 'react'
import { cn } from '@/utils'
import { useReducedMotion } from '@/hooks'
import { formatScore } from '@/utils'
import type { RiskBand } from '@/types'

interface RiskScoreGaugeProps {
  score:  number   // 0–1
  band:   RiskBand
}

const BAND_COLOR: Record<RiskBand, string> = {
  High:   'var(--risk-high)',
  Medium: 'var(--risk-medium)',
  Low:    'var(--risk-low)',
}

const BAND_TEXT_CLASS: Record<RiskBand, string> = {
  High:   'text-risk-high',
  Medium: 'text-risk-medium',
  Low:    'text-risk-low',
}

// SVG arc math
const SIZE    = 96
const STROKE  = 6
const R       = (SIZE - STROKE) / 2
const CIRC    = 2 * Math.PI * R
// Arc spans 270° (from 135° to 45° going clockwise — "open bottom" gauge)
const ARC_DEG = 270
const ARC_LEN = (ARC_DEG / 360) * CIRC

export const RiskScoreGauge: React.FC<RiskScoreGaugeProps> = ({ score, band }) => {
  const reduced  = useReducedMotion()
  const color    = BAND_COLOR[band]
  const textCls  = BAND_TEXT_CLASS[band]

  // Animated score value 0 → final (§7.2 Seq 3)
  // Fix #38: store rAF handle and cancel on cleanup to prevent updates after unmount.
  // Fix #39: include `reduced` in deps so preference changes are respected.
  const [displayed, setDisplayed] = useState(reduced ? score : 0)
  useEffect(() => {
    if (reduced) { setDisplayed(score); return }
    const start    = performance.now()
    const DURATION = 400
    let rafId: number
    const raf = (now: number) => {
      const t     = Math.min((now - start) / DURATION, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplayed(eased * score)
      if (t < 1) {
        rafId = requestAnimationFrame(raf)
      } else {
        setDisplayed(score)
      }
    }
    rafId = requestAnimationFrame(raf)
    return () => cancelAnimationFrame(rafId)
  }, [score, reduced])

  // Arc fill: strokeDashoffset for the animated fill
  const fillLen    = (displayed / 1) * ARC_LEN
  const dashOffset = ARC_LEN - fillLen
  // Rotation: start at 135° (bottom-left of circle)
  const rotate     = 135

  return (
    <div
      className="flex flex-col items-center gap-1"
      aria-label={`Risk score: ${formatScore(score)}, ${band} risk`}
    >
      {/* SVG arc gauge */}
      <div className="relative" style={{ width: SIZE, height: SIZE }}>
        <svg
          width={SIZE}
          height={SIZE}
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          aria-hidden
        >
          {/* Track (background arc) */}
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={R}
            fill="none"
            stroke="var(--border-hairline)"
            strokeWidth={STROKE}
            strokeDasharray={`${ARC_LEN} ${CIRC}`}
            strokeDashoffset={0}
            strokeLinecap="round"
            transform={`rotate(${rotate} ${SIZE / 2} ${SIZE / 2})`}
          />
          {/* Fill (animated) */}
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={R}
            fill="none"
            stroke={color}
            strokeWidth={STROKE}
            strokeDasharray={`${ARC_LEN} ${CIRC}`}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            transform={`rotate(${rotate} ${SIZE / 2} ${SIZE / 2})`}
            style={{ transition: reduced ? 'none' : 'stroke-dashoffset 0.4s cubic-bezier(0.2,0,0,1)' }}
          />
        </svg>

        {/* Center: score value (§4.2 monospace) */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn('text-xl font-bold font-mono leading-none', textCls)}>
            {formatScore(displayed)}
          </span>
          <span className="text-[10px] text-text-secondary mt-0.5 font-medium">score</span>
        </div>
      </div>

      {/* Band label below gauge (§10: color never only signal) */}
      <span className={cn('text-xs font-semibold uppercase tracking-wider', textCls)}>
        ● {band}
      </span>
    </div>
  )
}
