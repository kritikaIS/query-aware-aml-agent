/**
 * NetworkControls — zoom / reset / view-toggle controls
 * §10: keyboard accessible, aria-labels on all buttons
 */
import React from 'react'
import { ZoomIn, ZoomOut, RefreshCw, List } from 'lucide-react'
import { cn } from '@/utils'

interface NetworkControlsProps {
  onZoomIn:      () => void
  onZoomOut:     () => void
  onReset:       () => void
  onToggleView:  () => void
  tableView:     boolean
}

export const NetworkControls: React.FC<NetworkControlsProps> = ({
  onZoomIn, onZoomOut, onReset, onToggleView, tableView,
}) => {
  const btnBase = cn(
    'inline-flex items-center justify-center size-8 rounded-md',
    'border border-border-hairline bg-bg-panel',
    'text-text-secondary hover:text-text-primary hover:bg-bg-panel-raised',
    'transition-colors duration-[100ms]',
    'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan',
    'cursor-pointer'
  )

  return (
    <div className="flex flex-col gap-1" role="group" aria-label="Network view controls">
      <button type="button" onClick={onZoomIn}  className={btnBase} aria-label="Zoom in">
        <ZoomIn  size={13} aria-hidden />
      </button>
      <button type="button" onClick={onZoomOut} className={btnBase} aria-label="Zoom out">
        <ZoomOut size={13} aria-hidden />
      </button>
      <button type="button" onClick={onReset}   className={btnBase} aria-label="Reset view">
        <RefreshCw size={12} aria-hidden />
      </button>
      <button
        type="button"
        onClick={onToggleView}
        className={cn(btnBase, tableView && 'bg-accent-cyan/10 border-accent-cyan/30 text-accent-cyan')}
        aria-label={tableView ? 'Switch to graph view' : 'Switch to table view'}
        aria-pressed={tableView}
      >
        <List size={13} aria-hidden />
      </button>
    </div>
  )
}
