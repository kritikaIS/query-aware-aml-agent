/**
 * ExplanationPanel — renders the LLM explanation paragraph
 * Documented Requirement: §5.4
 * - Shows explanation text from ExecutionReport
 * - "highlights (subtle underline, no color change) every number that also
 *   appears in a chart or feature bar above it" — proves LLM restated facts
 * §4.2: sans-serif (system talking to you), numbers get subtle underline mark
 * §4.1: accent-violet for LLM-related elements
 */

import React from 'react'
import { cn } from '@/utils'

interface ExplanationPanelProps {
  explanation: string
  /** Numbers that appear in feature bars above — these get underlined in text */
  tracedValues: number[]
}

/**
 * Annotates the explanation text by wrapping numbers that are also present
 * in feature bars with a subtle underline — §5.4 "traceability principle."
 * Underline only, no color change.
 */
function annotateExplanation(text: string, tracedValues: number[]): React.ReactNode[] {
  if (tracedValues.length === 0) return [text]

  // Build a regex that matches any of the traced values as standalone numbers
  const escaped = tracedValues
    .map(v => v.toString().replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')

  const pattern = new RegExp(`(${escaped})`, 'g')
  const parts   = text.split(pattern)

  return parts.map((part, idx) => {
    const numVal = parseFloat(part)
    const isTraced = tracedValues.some(v => Math.abs(v - numVal) < 0.001)
    if (isTraced && !isNaN(numVal)) {
      return (
        <span
          key={idx}
          className="underline underline-offset-2 decoration-text-secondary/50 decoration-dotted"
          title="This value appears in the feature analysis above"
          aria-label={`${part} (also shown in feature bars above)`}
        >
          {part}
        </span>
      )
    }
    return <React.Fragment key={idx}>{part}</React.Fragment>
  })
}

export const ExplanationPanel: React.FC<ExplanationPanelProps> = ({
  explanation,
  tracedValues,
}) => {
  const annotated = annotateExplanation(explanation, tracedValues)

  return (
    <div className="flex flex-col gap-2">
      {/* §4.1: violet accent marks this as LLM-generated content */}
      <p className="text-[11px] font-semibold text-accent-violet uppercase tracking-wider">
        Agent Explanation
      </p>

      <div
        className={cn(
          'px-3 py-3 rounded-lg',
          'bg-bg-panel-raised border border-accent-violet/15',
          'text-sm text-text-secondary leading-relaxed'
        )}
      >
        {/* Opening quote mark — visual signal this is LLM narrative */}
        <span className="text-accent-violet/60 text-lg leading-none mr-1" aria-hidden>"</span>
        {annotated}
        <span className="text-accent-violet/60 text-lg leading-none ml-1" aria-hidden>"</span>
      </div>

      {/* Underline legend (§5.4 traceability) */}
      {tracedValues.length > 0 && (
        <p className="text-[10px] text-text-secondary">
          <span className="underline underline-offset-2 decoration-text-secondary/50 decoration-dotted mr-1">
            underlined numbers
          </span>
          also appear in the feature analysis above
        </p>
      )}
    </div>
  )
}
