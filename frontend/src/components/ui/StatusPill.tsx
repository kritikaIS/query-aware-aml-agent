/**
 * StatusPill — top bar dataset/env indicator (§5.1, §6)
 * Documented Requirement: §6 "StatusPill — dataset states"
 */

import React from 'react'
import { cn } from '@/utils'

type PillStatus = 'ok' | 'loading' | 'error' | 'offline'

interface StatusPillProps {
  status: PillStatus
  label: string
  sublabel?: string
  className?: string
}

const pillConfig: Record<PillStatus, { dot: string; border: string }> = {
  ok:      { dot: 'bg-risk-low',    border: 'border-risk-low/30' },
  loading: { dot: 'bg-accent-cyan', border: 'border-accent-cyan/30' },
  error:   { dot: 'bg-risk-high',   border: 'border-risk-high/30' },
  offline: { dot: 'bg-skipped',     border: 'border-skipped/30' },
}

export const StatusPill: React.FC<StatusPillProps> = ({
  status,
  label,
  sublabel,
  className,
}) => {
  const { dot, border } = pillConfig[status]

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1',
        'rounded-full text-xs font-medium',
        'bg-bg-panel border',
        border,
        className
      )}
      aria-label={`${label}${sublabel ? `: ${sublabel}` : ''}`}
    >
      <span
        className={cn('size-1.5 rounded-full', dot, status === 'loading' && 'animate-pulse')}
        aria-hidden
      />
      <span className="text-text-primary">{label}</span>
      {sublabel && (
        <span className="text-text-secondary">{sublabel}</span>
      )}
    </span>
  )
}
