/**
 * Spinner — loading indicator
 * Uses transform/opacity only — no layout thrash (§13 frame budget)
 */

import React from 'react'
import { cn } from '@/utils'

type SpinnerSize = 'sm' | 'md' | 'lg'

interface SpinnerProps {
  size?: SpinnerSize
  className?: string
  label?: string
}

const sizeClasses: Record<SpinnerSize, string> = {
  sm: 'size-4 border-2',
  md: 'size-6 border-2',
  lg: 'size-8 border-[3px]',
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  className,
  label = 'Loading…',
}) => (
  <span role="status" aria-label={label} className={cn('inline-flex', className)}>
    <span
      className={cn(
        'rounded-full border-current border-t-transparent animate-spin',
        'text-accent-cyan',
        sizeClasses[size]
      )}
      aria-hidden
    />
  </span>
)
