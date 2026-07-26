/**
 * Button — generic reusable button component
 * Documented Requirement: §10 keyboard navigable, focus rings (§4.1 accent-cyan)
 */

import React from 'react'
import { cn } from '@/utils'
import type { ButtonVariant, ButtonSize } from '@/types'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  iconLeft?: React.ReactNode
  iconRight?: React.ReactNode
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-accent-cyan text-bg-void font-semibold hover:opacity-90 active:opacity-80',
  secondary:
    'bg-bg-panel-raised text-text-primary border border-border-hairline hover:bg-bg-panel-raised/80',
  ghost:
    'text-text-secondary hover:text-text-primary hover:bg-bg-panel-raised',
  danger:
    'bg-risk-high/10 text-risk-high border border-risk-high/30 hover:bg-risk-high/20',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-7 px-3 text-xs gap-1.5',
  md: 'h-9 px-4 text-sm gap-2',
  lg: 'h-11 px-6 text-md gap-2',
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      iconLeft,
      iconRight,
      className,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        aria-busy={loading}
        className={cn(
          // Base
          'inline-flex items-center justify-center rounded-md font-medium',
          'transition-all duration-fast',
          'focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-cyan focus-visible:outline-offset-2',
          // Variant
          variantClasses[variant],
          // Size
          sizeClasses[size],
          // Disabled
          isDisabled && 'opacity-50 cursor-not-allowed pointer-events-none',
          className
        )}
        {...props}
      >
        {loading ? (
          <span className="size-4 rounded-full border-2 border-current border-t-transparent animate-spin" aria-hidden />
        ) : (
          iconLeft
        )}
        {children}
        {!loading && iconRight}
      </button>
    )
  }
)

Button.displayName = 'Button'
