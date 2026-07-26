/**
 * ToolStatusBadge — tiny status chip inside ToolCard
 * Documented Requirement: §5.2 queued → running → done status chips
 * §10: color never only signal — text label always present
 */

import React from 'react'
import { cn } from '@/utils'
import type { ToolState } from '@/types'

interface ToolStatusBadgeProps {
  state: ToolState
}

const CONFIG: Record<ToolState, { label: string; classes: string }> = {
  queued:  { label: 'queued',   classes: 'bg-bg-panel-raised text-text-secondary border-border-hairline' },
  running: { label: 'running',  classes: 'bg-accent-cyan/10  text-accent-cyan   border-accent-cyan/30' },
  done:    { label: '✓ done',   classes: 'bg-risk-low/10     text-risk-low      border-risk-low/30' },
  skipped: { label: 'skipped',  classes: 'bg-skipped/20      text-text-secondary border-skipped/40' },
  error:   { label: 'error',    classes: 'bg-risk-high/10    text-risk-high     border-risk-high/30' },
}

export const ToolStatusBadge: React.FC<ToolStatusBadgeProps> = ({ state }) => {
  const { label, classes } = CONFIG[state]
  return (
    <span
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium border',
        classes
      )}
    >
      {label}
    </span>
  )
}
