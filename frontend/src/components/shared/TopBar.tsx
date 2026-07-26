/**
 * TopBar — persistent App Shell header (§3)
 * Documented Requirement: "Top Bar: logo · dataset status · env indicator · raw-JSON toggle"
 *
 * Left:  AML AGENT · SUSPICIOUS ACTIVITY DETECTION  (§5.1 wireframe)
 * Right: ● dataset✓ (StatusPill) · ENV indicator · [{ }] raw JSON toggle placeholder
 *
 * Accessibility (§10):
 * - role="banner" is on the <header> in AppShell — TopBar only provides content
 * - Dataset pill has aria-label with full row count text
 * - JSON toggle button has aria-label
 * - All interactive elements are keyboard focusable
 */

import React from 'react'
import { Braces } from 'lucide-react'
import { StatusPill } from '@/components/ui'
import { useUiStore, useDatasetStore } from '@/stores'
import { formatCount } from '@/utils'
import { cn } from '@/utils'

interface TopBarProps {
  className?: string
}

export const TopBar: React.FC<TopBarProps> = ({ className }) => {
  const jsonInspectorOpen    = useUiStore((s) => s.jsonInspectorOpen)
  const setJsonInspectorOpen = useUiStore((s) => s.setJsonInspectorOpen)
  const currentView          = useUiStore((s) => s.currentView)
  const datasetStatus        = useDatasetStore((s) => s.status)

  const env = import.meta.env.MODE?.toUpperCase() ?? 'DEV'

  // Dataset pill status — §5.1: "Dataset status pill shows row counts / freshness"
  const pillStatus = datasetStatus.loaded ? 'ok' : 'loading'
  const pillLabel  = datasetStatus.loaded
    ? `${formatCount(datasetStatus.rowCount ?? 0)} rows`
    : 'Loading dataset…'
  const pillSublabel = datasetStatus.loaded && datasetStatus.freshness
    ? datasetStatus.freshness
    : undefined

  // JSON toggle is available on results screen and above (§5.5 "one click from anywhere")
  // Disabled on query/plan screens where no report exists yet
  const jsonToggleDisabled = currentView === 'query'

  return (
    <div
      className={cn(
        'h-14 px-4 tablet:px-6 flex items-center justify-between gap-4',
        className
      )}
    >
      {/* ── Left: Logo / branding (§3, §5.1 wireframe) ── */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Monospace dot for command-center feel (§2 principle 2) */}
        <span className="size-2 rounded-full bg-accent-cyan shrink-0" aria-hidden />
        <div className="flex items-baseline gap-1.5">
          <span className="text-sm font-bold text-text-primary tracking-widest uppercase">
            AML Agent
          </span>
          <span
            className="hidden tablet:inline text-xs text-text-secondary tracking-wide"
            aria-hidden
          >
            · Suspicious Activity Detection
          </span>
        </div>
      </div>

      {/* ── Right: dataset status · env · JSON toggle (§3, §5.1) ── */}
      <div className="flex items-center gap-2 tablet:gap-3">

        {/* Dataset status pill (§5.1, §6 StatusPill component) */}
        <StatusPill
          status={pillStatus}
          label={pillLabel}
          sublabel={pillSublabel}
          aria-label={
            datasetStatus.loaded
              ? `Dataset loaded: ${formatCount(datasetStatus.rowCount ?? 0)} transactions, refreshed ${datasetStatus.freshness}`
              : 'Dataset loading'
          }
        />

        {/* Environment indicator (§3) — monospace per §4.2 */}
        <span
          className="hidden tablet:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium border border-border-hairline bg-bg-panel text-text-secondary"
          aria-label={`Environment: ${env}`}
        >
          {env}
        </span>

        {/* Raw JSON toggle placeholder (§3, §5.5) */}
        {/* Functional implementation deferred to JSON Inspector screen */}
        <button
          type="button"
          onClick={() => !jsonToggleDisabled && setJsonInspectorOpen(!jsonInspectorOpen)}
          disabled={jsonToggleDisabled}
          aria-label="View raw JSON output"
          aria-pressed={jsonInspectorOpen}
          className={cn(
            'inline-flex items-center gap-1.5 h-7 px-2.5',
            'rounded-md text-xs font-medium',
            'border border-border-hairline',
            'transition-colors duration-[100ms]',
            jsonToggleDisabled
              ? 'opacity-30 cursor-not-allowed bg-bg-panel text-text-secondary'
              : jsonInspectorOpen
                ? 'bg-accent-violet/10 border-accent-violet/40 text-accent-violet'
                : 'bg-bg-panel text-text-secondary hover:text-text-primary hover:bg-bg-panel-raised hover:border-accent-violet/30',
            'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan'
          )}
        >
          <Braces size={12} aria-hidden />
          <span className="hidden tablet:inline">JSON</span>
        </button>
      </div>
    </div>
  )
}
