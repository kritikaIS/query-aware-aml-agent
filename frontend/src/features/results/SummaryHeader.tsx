/**
 * SummaryHeader — top bar of the Results Dashboard
 * Documented Requirement: §5.3 wireframe:
 *   "◂ Query recap · plan summary · [View raw JSON ⧉]"
 *
 * §3: Raw JSON toggle is always available from any screen
 * §4.1: accent-violet for the JSON button (LLM-related elements)
 */

import React from 'react'
import { ArrowLeft, ExternalLink } from 'lucide-react'
import { cn } from '@/utils'
import { useUiStore } from '@/stores'

interface SummaryHeaderProps {
  query:        string
  toolsInvoked: number
  toolsSkipped: number
}

export const SummaryHeader: React.FC<SummaryHeaderProps> = ({
  query,
  toolsInvoked,
  toolsSkipped,
}) => {
  const setView              = useUiStore((s) => s.setView)
  const setJsonInspectorOpen = useUiStore((s) => s.setJsonInspectorOpen)
  const jsonInspectorOpen    = useUiStore((s) => s.jsonInspectorOpen)

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* ◂ Back to plan (§5.3 wireframe "◂ Query recap") */}
      <button
        type="button"
        onClick={() => setView('plan')}
        className={cn(
          'inline-flex items-center gap-1.5 text-xs text-text-secondary',
          'hover:text-text-primary transition-colors duration-[100ms]',
          'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan rounded',
          'cursor-pointer'
        )}
        aria-label="Return to execution plan"
      >
        <ArrowLeft size={12} aria-hidden />
        <span>Plan</span>
      </button>

      <span className="text-border-hairline text-xs" aria-hidden>·</span>

      {/* Query recap */}
      <span className="text-xs text-text-secondary truncate max-w-xs" title={query}>
        <span className="text-text-secondary">"</span>
        <span className="text-text-primary">{query}</span>
        <span className="text-text-secondary">"</span>
      </span>

      <span className="text-border-hairline text-xs" aria-hidden>·</span>

      {/* Plan summary */}
      <span className="text-xs text-text-secondary hidden tablet:inline">
        <span className="font-mono text-text-primary">{toolsInvoked}</span> tools invoked
        {toolsSkipped > 0 && (
          <>
            {' · '}
            <span className="font-mono text-text-secondary line-through">{toolsSkipped}</span>
            <span> skipped</span>
          </>
        )}
      </span>

      {/* Push JSON toggle to right */}
      <div className="ml-auto">
        {/* [View raw JSON ⧉] — §5.3 wireframe, §5.5 functionality deferred */}
        <button
          type="button"
          onClick={() => setJsonInspectorOpen(!jsonInspectorOpen)}
          aria-label="View raw JSON output"
          aria-pressed={jsonInspectorOpen}
          className={cn(
            'inline-flex items-center gap-1.5 h-7 px-2.5 rounded-md text-xs font-medium',
            'border transition-colors duration-[100ms]',
            jsonInspectorOpen
              ? 'bg-accent-violet/10 border-accent-violet/40 text-accent-violet'
              : 'bg-bg-panel border-border-hairline text-text-secondary hover:text-text-primary hover:bg-bg-panel-raised hover:border-accent-violet/30',
            'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan',
            'cursor-pointer'
          )}
        >
          <span className="font-mono text-[11px]">&#123;&#125;</span>
          <span className="hidden tablet:inline">View raw JSON</span>
          <ExternalLink size={10} aria-hidden />
        </button>
      </div>
    </div>
  )
}
