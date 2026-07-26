/**
 * SearchBox — large command-style input
 * Documented Requirement: §5.1 "large centered command input — cursor blinks with
 * soft cyan glow" — foundational component for the Query Console screen.
 * NOT the Query Console itself; only the input primitive.
 */

import React from 'react'
import { Search } from 'lucide-react'
import { cn } from '@/utils'

// Omit 'onSubmit' from the base TextareaHTMLAttributes to avoid collision with
// the native SubmitEvent-typed onSubmit handler. We provide a custom string-valued one.
interface SearchBoxProps extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, 'onSubmit'> {
  onSubmit?: (value: string) => void
}

export const SearchBox = React.forwardRef<HTMLTextAreaElement, SearchBoxProps>(
  ({ onSubmit, className, ...props }, ref) => {
    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Enter without Shift submits (§5.1)
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        const value = (e.currentTarget.value ?? '').trim()
        if (value && onSubmit) onSubmit(value)
      }
      props.onKeyDown?.(e)
    }

    return (
      <div className="relative flex items-start">
        <Search
          size={16}
          className="absolute left-4 top-4 text-text-secondary pointer-events-none shrink-0"
          aria-hidden
        />
        <textarea
          ref={ref}
          rows={1}
          spellCheck={false}
          className={cn(
            'w-full resize-none pl-10 pr-4 py-3.5',
            'bg-bg-panel border border-border-hairline rounded-lg',
            'text-base text-text-primary placeholder:text-text-secondary',
            'transition-all duration-instant',
            // Cyan glow on focus — §5.1 "cursor blinks with soft cyan glow"
            'focus-visible:outline-none focus-visible:border-accent-cyan focus-visible:ring-1 focus-visible:ring-accent-cyan',
            'cursor-glow',
            className
          )}
          onKeyDown={handleKeyDown}
          {...props}
        />
      </div>
    )
  }
)

SearchBox.displayName = 'SearchBox'
