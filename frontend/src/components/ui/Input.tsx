/**
 * Input — generic text input
 * Documented Requirement: §10 keyboard navigable, focus ring accent-cyan (§4.1)
 */

import React from 'react'
import { cn } from '@/utils'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, className, id, ...props }, ref) => {
    // Fix #44: always call useId at top level; then optionally use the prop id
    const generatedId = React.useId()
    const inputId     = id ?? generatedId

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-xs font-medium text-text-secondary">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            'h-9 w-full px-3 rounded-md text-sm',
            'bg-bg-panel border border-border-hairline',
            'text-text-primary placeholder:text-text-secondary',
            'transition-all duration-instant',
            'focus-visible:outline-none focus-visible:border-accent-cyan focus-visible:ring-1 focus-visible:ring-accent-cyan',
            error && 'border-risk-high focus-visible:border-risk-high focus-visible:ring-risk-high',
            className
          )}
          aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
          aria-invalid={Boolean(error)}
          {...props}
        />
        {error && (
          <p id={`${inputId}-error`} role="alert" className="text-xs text-risk-high">
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={`${inputId}-hint`} className="text-xs text-text-secondary">
            {hint}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
