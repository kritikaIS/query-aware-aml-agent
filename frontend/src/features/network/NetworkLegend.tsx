/**
 * NetworkLegend — colour/size legend for the network graph
 * §10: icon + text + colour (never colour alone)
 */
import React from 'react'
import type { AmlPattern } from '@/types'

const PATTERN_LABEL: Record<string, string> = {
  structuring:   'Structuring',
  smurfing:      'Smurfing',
  layering:      'Layering',
  rapid_cashout: 'Rapid Cash-Out',
}

interface NetworkLegendProps {
  patterns: AmlPattern[]
}

export const NetworkLegend: React.FC<NetworkLegendProps> = ({ patterns }) => (
  <div className="flex flex-col gap-3 text-xs">
    {/* Risk band legend */}
    <div>
      <p className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
        Risk Band
      </p>
      <div className="flex flex-col gap-1">
        {([
          { band: 'High',   color: 'bg-risk-high',   label: '● High'   },
          { band: 'Medium', color: 'bg-risk-medium',  label: '● Medium' },
          { band: 'Low',    color: 'bg-risk-low',     label: '● Low'    },
        ] as const).map(({ color, label }) => (
          <div key={label} className="flex items-center gap-2">
            <span className={`size-2.5 rounded-full ${color} shrink-0`} aria-hidden />
            <span className="text-text-secondary">{label}</span>
          </div>
        ))}
      </div>
    </div>

    {/* Node size */}
    <div>
      <p className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
        Node Size
      </p>
      <div className="flex items-center gap-2">
        <span className="size-2 rounded-full bg-text-secondary/50 shrink-0" aria-hidden />
        <span className="text-text-secondary">Low risk score</span>
      </div>
      <div className="flex items-center gap-2 mt-0.5">
        <span className="size-4 rounded-full bg-text-secondary/50 shrink-0" aria-hidden />
        <span className="text-text-secondary">High risk score</span>
      </div>
    </div>

    {/* AML patterns present */}
    {patterns.filter(Boolean).length > 0 && (
      <div>
        <p className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
          AML Patterns
        </p>
        {patterns.filter(Boolean).map(p => (
          <div key={p} className="flex items-center gap-2 mb-0.5">
            <span className="size-1.5 rounded-full bg-accent-cyan shrink-0" aria-hidden />
            <span className="text-text-secondary font-mono">{PATTERN_LABEL[p!] ?? p}</span>
          </div>
        ))}
      </div>
    )}

    {/* Edge meaning */}
    <div>
      <p className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider mb-1.5">
        Edges
      </p>
      <div className="flex items-center gap-2">
        <span className="w-6 h-px bg-accent-cyan/50 shrink-0" aria-hidden />
        <span className="text-text-secondary">Co-flagged pattern</span>
      </div>
    </div>
  </div>
)
