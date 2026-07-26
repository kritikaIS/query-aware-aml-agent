/**
 * JsonToolbar — toolbar for the Raw JSON Inspector
 * Documented Requirement: §6 "<JsonTree> Search + copy-path on hover"
 * Task brief: Copy JSON, Expand All, Collapse All, Search
 *
 * §4.2: monospace for machine values (JSON, paths)
 * §10: all buttons keyboard accessible, copy announces via aria-live
 * §7.1: toolbar entrance motion-fast (180ms)
 */

import React, { useState } from 'react'
import { Copy, Maximize2, Minimize2, Search, Check } from 'lucide-react'
import { cn } from '@/utils'

interface JsonToolbarProps {
  onExpandAll:   () => void
  onCollapseAll: () => void
  searchQuery:   string
  onSearch:      (q: string) => void
  /** Full JSON string for copy-to-clipboard */
  rawJson:       string
}

export const JsonToolbar: React.FC<JsonToolbarProps> = ({
  onExpandAll,
  onCollapseAll,
  searchQuery,
  onSearch,
  rawJson,
}) => {
  const [copied, setCopied] = useState(false)
  const [copyAnnounce, setCopyAnnounce] = useState('')

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(rawJson)
      setCopied(true)
      setCopyAnnounce('Copied to clipboard')
      setTimeout(() => {
        setCopied(false)
        setCopyAnnounce('')
      }, 2000)
    } catch {
      setCopyAnnounce('Copy failed')
      setTimeout(() => setCopyAnnounce(''), 2000)
    }
  }

  const buttonBase = cn(
    'inline-flex items-center gap-1.5 h-7 px-2.5 rounded text-xs font-medium',
    'border border-border-hairline',
    'transition-colors duration-[100ms]',
    'text-text-secondary hover:text-text-primary hover:bg-bg-panel-raised',
    'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan',
    'cursor-pointer'
  )

  return (
    <div className="flex items-center gap-2 flex-wrap">

      {/* Search input */}
      <div className="relative flex-1 min-w-[160px]">
        <Search
          size={12}
          className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none"
          aria-hidden
        />
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Search keys or values…"
          aria-label="Search JSON keys and values"
          className={cn(
            'h-7 w-full pl-7 pr-3 rounded border border-border-hairline',
            'bg-bg-panel text-xs font-mono text-text-primary',
            'placeholder:text-text-secondary',
            'focus-visible:outline-none focus-visible:border-accent-cyan focus-visible:ring-1 focus-visible:ring-accent-cyan',
            'transition-all duration-[100ms]'
          )}
        />
      </div>

      {/* Expand All */}
      <button
        type="button"
        onClick={onExpandAll}
        aria-label="Expand all JSON nodes"
        className={buttonBase}
      >
        <Maximize2 size={11} aria-hidden />
        <span className="hidden tablet:inline">Expand</span>
      </button>

      {/* Collapse All */}
      <button
        type="button"
        onClick={onCollapseAll}
        aria-label="Collapse all JSON nodes"
        className={buttonBase}
      >
        <Minimize2 size={11} aria-hidden />
        <span className="hidden tablet:inline">Collapse</span>
      </button>

      {/* Copy JSON */}
      <button
        type="button"
        onClick={handleCopy}
        aria-label={copied ? 'Copied to clipboard' : 'Copy full JSON to clipboard'}
        className={cn(
          buttonBase,
          copied && 'text-risk-low border-risk-low/30 bg-risk-low/8 hover:bg-risk-low/10'
        )}
      >
        {copied
          ? <Check size={11} className="text-risk-low" aria-hidden />
          : <Copy size={11} aria-hidden />
        }
        <span className="hidden tablet:inline">
          {copied ? 'Copied!' : 'Copy JSON'}
        </span>
      </button>

      {/* §10: aria-live announces copy action to screen readers */}
      <span
        role="status"
        aria-live="polite"
        className="sr-only"
      >
        {copyAnnounce}
      </span>
    </div>
  )
}
