/**
 * useCountUp — count-up animation for KPI tiles
 * Documented Requirement: §7.2 seq 4 "ease-out count from 0 → final value over
 * 600ms, only on first mount, never on re-render"
 * §10: disabled entirely when prefers-reduced-motion is set
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Runs once on mount only — by design (§7.2 seq 4)

  return current
}
