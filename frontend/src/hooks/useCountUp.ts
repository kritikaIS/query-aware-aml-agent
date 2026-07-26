/**
 * useCountUp — count-up animation for KPI tiles
 * Documented Requirement: §7.2 seq 4 "ease-out count from 0 → final value over
 * 600ms, only on first mount, never on re-render"
 * §10: disabled entirely when prefers-reduced-motion is set
 *
 * Fix: replaced empty dep array `[]` with `[target, reduced]`.
 * The `startedRef` guard ensures the animation still only runs once per
 * unique target value, not on every render. When KpiTile remounts (e.g.
 * after the results view is re-entered), `startedRef` resets to false
 * because it is a new hook instance, so the count-up plays correctly.
 */

import { useEffect, useRef, useState } from 'react'
import { useReducedMotion } from './useReducedMotion'

const DURATION_MS = 600

export function useCountUp(target: number, startOnMount = true): number {
  const reduced = useReducedMotion()
  const [current, setCurrent] = useState(reduced ? target : 0)
  const rafRef = useRef<number | null>(null)
  const startedRef = useRef(false)

  useEffect(() => {
    // Instant final state if reduced motion (§7.3, §10)
    if (reduced) {
      setCurrent(target)
      return
    }

    // Reset animation state when target changes (e.g. component remount
    // with a new value, or first mount with a non-zero target).
    startedRef.current = false
    setCurrent(0)

    if (!startOnMount || startedRef.current) return
    startedRef.current = true

    const startTime = performance.now()
    const startVal = 0

    const animate = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / DURATION_MS, 1)
      // ease-out: 1 - (1 - t)^3
      const eased = 1 - Math.pow(1 - progress, 3)
      setCurrent(Math.round(startVal + (target - startVal) * eased))

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate)
      }
    }

    rafRef.current = requestAnimationFrame(animate)

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  // Re-run when the target value or motion preference changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, reduced])

  return current
}
