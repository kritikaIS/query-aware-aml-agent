/**
 * NetworkTableView — accessible tabular alternative to the graph
 * §10: "Alternative table/list view" requirement
 * Keyboard navigable, all data accessible without mouse
 */
import React from 'react'
import { cn, formatScore } from '@/utils'
import type { GraphNode } from './adapter'

const BAND_COLOR: Record<string, string> = {
  High:   'text-risk-high',
  Medium: 'text-risk-medium',
  Low:    'text-risk-low',
}

interface NetworkTableViewProps {
  nodes:        GraphNode[]
  selectedId:   string | null
  onSelect:     (id: string) => void
}

export const NetworkTableView: React.FC<NetworkTableViewProps> = ({
  nodes, selectedId, onSelect,
}) => (
  <div
    role="table"
    aria-label="Flagged entity network — table view"
    className="w-full overflow-auto"
  >
    {/* Header */}
    <div role="row" className="grid grid-cols-5 px-3 py-2 text-[10px] font-semibold text-text-secondary uppercase tracking-wider border-b border-border-hairline bg-bg-panel-raised">
      <span role="columnheader">Customer</span>
      <span role="columnheader">Risk Band</span>
      <span role="columnheader">Score</span>
      <span role="columnheader">AML Pattern</span>
      <span role="columnheader">Action</span>
    </div>

    {nodes.map(node => (
      <div
        key={node.id}
        role="row"
        tabIndex={0}
        aria-selected={selectedId === node.id}
        onClick={() => onSelect(node.id)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(node.id) } }}
        className={cn(
          'grid grid-cols-5 px-3 py-2.5 text-xs cursor-pointer',
          'border-b border-border-hairline/50',
          'transition-colors duration-[100ms]',
          selectedId === node.id
            ? 'bg-accent-cyan/10 border-accent-cyan/30'
            : 'hover:bg-bg-panel-raised',
          'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-accent-cyan'
        )}
      >
        <span className="font-mono text-text-primary">{node.id}</span>
        <span className={cn('font-semibold', BAND_COLOR[node.risk_band])}>
          ● {node.risk_band}
        </span>
        <span className="font-mono text-text-secondary">{formatScore(node.risk_score)}</span>
        <span className="font-mono text-text-secondary">{node.aml_pattern ?? '—'}</span>
        <span className="text-text-secondary truncate">{node.action}</span>
      </div>
    ))}
  </div>
)
