/**
 * useTypewriter — typewriter text reveal for the reasoning ticker
 * Documented Requirement: §5.2 "streams planner's reasoning string token-by-token,
 * typewriter-style"; §7.1 motion-stream 20–35ms/char linear; §7.2 "skippable on
 * click — jumps to full text"; §10 prefers-reduced-motion shows full text instantly
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { useReducedMotion } from './useReducedMotion'
import { MOTION } from '@/constants'

interface TypewriterOptions {
  text: string
  /** Called when animation completes */
  onComplete?: () => void
}

interface TypewriterResult {
  displayed: string
  isComplete: boolean
  skip: () => void
}

export function useTypewriter({ text, onComplete }: TypewriterOptions): TypewriterResult {
  const reduced = useReducedMotion()
  const [displayed, setDisplayed] = useState('')
  const [isComplete, setIsComplete] = useState(false)
  const indexRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const skippedRef = useRef(false)

  const complete = useCallback(() => {
    setDisplayed(text)
    setIsComplete(true)
    onComplete?.()
  }, [text, onComplete])

  const skip = useCallback(() => {
    skippedRef.current = true
    if (timerRef.current) clearTimeout(timerRef.current)
    complete()
  }, [complete])

  useEffect(() => {
    if (reduced) {
      complete()
      return
    }

    // Reset when text changes (new streaming content)
    indexRef.current = 0
    skippedRef.current = false
    setDisplayed('')
    setIsComplete(false)

    const tick = () => {
      if (skippedRef.current) return
      const idx = indexRef.current
      if (idx >= text.length) {
        setIsComplete(true)
        onComplete?.()
        return
      }
      setDisplayed(text.slice(0, idx + 1))
      indexRef.current = idx + 1
      timerRef.current = setTimeout(tick, MOTION.STREAM_MS)
    }

    timerRef.current = setTimeout(tick, MOTION.STREAM_MS)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [text, reduced, complete, onComplete])

  return { displayed, isComplete, skip }
}
