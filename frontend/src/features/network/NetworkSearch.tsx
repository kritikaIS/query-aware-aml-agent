/**
 * NetworkSearch — search box to focus a customer node by ID
 * §10: aria-label, keyboard navigable
 */
import React from 'react'
import { Search } from 'lucide-react'
import { cn } from '@/utils'

interface NetworkSearchProps {
  value:    string
  onChange: (v: string) => void
}

export const NetworkSearch: React.FC<NetworkSearchProps> = ({ value, onChange }) => (
  <div className="relative">
    <Search
      size={12}
      className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none"
      aria-hidden
    />
    <input
      type="search"
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder="Search customer ID…"
      aria-label="Search customer by ID"
      className={cn(
        'h-7 w-44 pl-7 pr-2.5 rounded border border-border-hairline',
        'bg-bg-panel text-[11px] font-mono text-text-primary',
        'placeholder:text-text-secondary',
        'focus-visible:outline-none focus-visible:border-accent-cyan focus-visible:ring-1 focus-visible:ring-accent-cyan',
        'transition-all duration-[100ms]'
      )}
    />
  </div>
)
