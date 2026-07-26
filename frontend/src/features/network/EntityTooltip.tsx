/**
 * EntityTooltip — tooltip shown on node hover/focus
 * Shows customer_id, risk_score, pattern, top features
 * §10: role="tooltip", accessible text
 */
import React from 'react'
import { cn } from '@/utils'
import { formatScore, formatZScore } from '@/utils'
import type { GraphNode } from './adapter'

interface EntityTooltipProps {
  node:   GraphNode
  x:      number   // canvas pixel x
  y:      number   // canvas pixel y
  width:  number   // canvas width (for boundary clamping)
  height: number   // canvas height
}

const BAND_COLOR: Record<string, string> = {
  High:   'text-risk-high',
  Medium: 'text-risk-medium',
  Low:    'text-risk-low',
}

export const EntityTooltip: React.FC<EntityTooltipProps> = ({
  node, x, y, width, height,
}) => {
  // Clamp so tooltip never overflows canvas edges
  const TIP_W = 200
  const TIP_H = 140  // approximate
  const left  = Math.min(x + 12, width  - TIP_W - 8)
  const top   = Math.min(y - 8,  height - TIP_H - 8)

  return (
    <div
      role="tooltip"
      id={`network-tip-${node.id}`}
      className={cn(
        'absolute pointer-events-none z-tooltip',
        'panel rounded-lg px-3 py-2.5 shadow-raised',
        'text-xs min-w-[180px] max-w-[220px]',
      )}
      style={{ left, top }}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className="font-mono font-semibold text-text-primary">
          Customer {node.id}
        </span>
        <span className={cn('font-semibold', BAND_COLOR[node.risk_band])}>
          ● {node.risk_band}
        </span>
      </div>

      {/* Score */}
      <div className="flex items-center gap-1.5 text-text-secondary mb-1">
        <span>Score:</span>
        <span className="font-mono text-text-primary">{formatScore(node.risk_score)}</span>
      </div>

      {/* Pattern */}
      {node.aml_pattern && (
        <div className="text-text-secondary mb-1.5">
          <span className="font-mono text-accent-cyan">{node.aml_pattern}</span>
        </div>
      )}

      {/* Top feature */}
      {node.features.length > 0 && (
        <div className="pt-1.5 border-t border-border-hairline/50">
          <p className="text-[10px] text-text-secondary mb-0.5 uppercase tracking-wider">
            Top feature
          </p>
          <span className="font-mono text-text-secondary">
            {node.features[0].feature}
            <span className="text-accent-cyan ml-1.5">
              {formatZScore(node.features[0].z_score)}
            </span>
          </span>
        </div>
      )}

      {/* Action */}
      <div className="mt-1 text-[10px] text-text-secondary">
        {node.action}
      </div>
    </div>
  )
}
