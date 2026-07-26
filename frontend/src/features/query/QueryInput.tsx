/**
 * QueryInput — the large centered command input.
 * Documented Requirement: §5.1
 *  - "Large, centered command input"
 *  - "cursor blinks with a soft cyan glow (--accent-cyan)"
 *  - "reinforcing 'you're talking to an agent,' not filling out a form"
 *  - Search icon (⌨ in wireframe, Search icon from Lucide per §11 stack)
 *
 * Animations:
 * - Focus: cyan border + glow ring (motion-instant, CSS) (§7.1)
 * - No other animations — this is a pure input, not a layout element
 *
 * Accessibility:
 * - aria-label on textarea (§10)
 * - Enter (no Shift) submits — Shift+Enter adds newline
 * - Visually: placeholder describes purpose
 */

import React, { useRef, useEffect } from 'react'
import { Terminal } from 'lucide-react'
import { cn } from '@/utils'

interface QueryInputProps {
  value: string
  onChange: (value: string) => void
  onSubmit: (value: string) => void
  disabled?: boolean
  autoFocus?: boolean
}

export const QueryInput: React.FC<QueryInputProps> = ({
  value,
  onChange,
  onSubmit,
  disabled = false,
  autoFocus = true,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-focus on mount — §5.1 entry state is the query console
  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [autoFocus])

  // Auto-resize textarea height to content
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.max(el.scrollHeight, 56)}px`
  }, [value])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter without Shift submits (§5.1 keyboard shortcut)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      const trimmed = value.trim()
      if (trimmed && !disabled) onSubmit(trimmed)
    }
  }

  return (
    <div className="relative w-full group">
      {/* Search/terminal icon — §5.1 wireframe shows ⌨ icon */}
      <Terminal
        size={18}
        className={cn(
          'absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none',
          'transition-colors duration-[100ms]',
          value.length > 0
            ? 'text-accent-cyan'
            : 'text-text-secondary group-focus-within:text-accent-cyan'
        )}
        aria-hidden
      />

      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        rows={1}
        spellCheck={false}
        aria-label="AML query input — type a question about your transaction data"
        aria-multiline="true"
        placeholder="Ask the agent anything about this data."
        className={cn(
          // Layout
          'w-full resize-none',
          'pl-11 pr-5 py-4',
          // Typography: Inter body, not monospace (user input is natural language, §4.2)
          'text-base font-normal leading-relaxed',
          'text-text-primary placeholder:text-text-secondary',
          // Surface: bg-panel with hairline border (§4.3)
          'bg-bg-panel border border-border-hairline rounded-lg',
          // Transition: motion-instant on focus (§7.1)
          'transition-all duration-[100ms] ease-out',
          // Cyan focus glow — §5.1 "cursor blinks with a soft cyan glow"
          'focus-visible:outline-none',
          'focus-visible:border-accent-cyan',
          'focus-visible:ring-2 focus-visible:ring-accent-cyan/20',
          'focus-visible:shadow-[0_0_0_2px_rgba(62,214,196,0.15),0_0_16px_rgba(62,214,196,0.1)]',
          // Disabled
          disabled && 'opacity-50 cursor-not-allowed',
          // No scrollbar in collapsed state
          'overflow-hidden'
        )}
        style={{ minHeight: '56px' }}
      />

      {/* Keyboard hint (§10 keyboard shortcut) — desktop only */}
      <span className="hidden desktop:flex absolute right-3 bottom-3 items-center gap-1 text-xs text-text-secondary pointer-events-none select-none">
        <kbd className="px-1.5 py-0.5 rounded border border-border-hairline bg-bg-panel-raised font-mono text-[10px]">Enter</kbd>
        <span>to run</span>
      </span>
    </div>
  )
}
