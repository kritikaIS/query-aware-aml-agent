/**
 * Badge — generic label chip
 * Documented Requirement: §6 Component Library, §10 color never only signal
 */

import React from 'react'
import { cn } from '@/utils'
import type { BadgeVariant } from '@/types'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

const variantClasses: Record<BadgeVariant, string> = {
  default:  'bg-bg-panel-raised text-text-secondary border border-border-hairline',
  low:      'bg-risk-low/10 text-risk-low border border-risk-low/30',
  medium:   'bg-risk-medium/10 text-risk-medium border border-risk-medium/30',
  high:     'bg-risk-high/10 text-risk-high border border-risk-high/30',
  skipped:  'bg-skipped/20 text-text-secondary border border-skipped/30',
  active:   'bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/30',
  done:     'bg-risk-low/10 text-risk-low border border-risk-low/30',
  queued:   'bg-bg-panel-raised text-text-secondary border border-border-hairline',
  error:    'bg-risk-high/10 text-risk-high border border-risk-high/30',
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ variant = 'default', className, children, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5',
        'rounded-full text-xs font-medium font-mono',
        variantClasses[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
)

Badge.displayName = 'Badge'
