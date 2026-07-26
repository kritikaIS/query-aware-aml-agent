/**
 * JsonBreadcrumb — shows the dot-notation path for the selected/hovered JSON node
 * Documented Requirement: §6 "<JsonTree> Search + copy-path on hover"
 * Displays the path as a navigable breadcrumb trail.
 * §4.2: path in monospace (machine-generated value)
 */

import React from 'react'
import { cn } from '@/utils'

interface JsonBreadcrumbProps {
  path: string[]   // e.g. ['execution_plan', 'steps', '0', 'tool']
}

export const JsonBreadcrumb: React.FC<JsonBreadcrumbProps> = ({ path }) => {
  if (path.length === 0) {
    return (
      <span className="text-[10px] font-mono text-text-secondary/60 italic">
        Hover a key to see its path
      </span>
    )
  }

  return (
    <div
      className="flex items-center gap-0.5 flex-wrap"
      aria-label={`Current path: ${path.join('.')}`}
    >
      <span className="text-[10px] font-mono text-accent-cyan">$</span>
      {path.map((segment, idx) => (
        <span key={idx} className="flex items-center gap-0.5">
          <span className="text-[10px] font-mono text-text-secondary/60">.</span>
          <span className={cn(
            'text-[10px] font-mono',
            idx === path.length - 1
              ? 'text-text-primary'
              : 'text-text-secondary'
          )}>
            {segment}
          </span>
        </span>
      ))}
    </div>
  )
}
