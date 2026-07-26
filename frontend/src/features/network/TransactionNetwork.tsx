/**
 * TransactionNetwork — §8 "Smurfing network graph (stretch)"
 *
 * Fully independent feature. Reads from reportStore.
 * Adapter layer decouples backend schema from UI.
 *
 * Documented mapping:
 *   §8: D3 force-directed, only rendered when aml_pattern_matched present
 *   §4.1: risk colors, accent-cyan for selection
 *   §10: keyboard controls, table fallback, reduced motion
 *   §9: responsive canvas, mobile graceful degradation
 *   §13: all D3 deps lazy-loaded, graph memoised
 */

import React, {
  lazy, Suspense, useRef, useState, useMemo, useCallback,
} from 'react'
import { motion } from 'framer-motion'
import { Network } from 'lucide-react'
import { useReportStore, useUiStore } from '@/stores'
import { MOCK_EXECUTION_REPORT } from '@/features/results/mock'
import { buildGraphData, filterGraphData } from './adapter'
import { NetworkControls } from './NetworkControls'
import { NetworkFilters } from './NetworkFilters'
import { NetworkSearch } from './NetworkSearch'
import { NetworkLegend } from './NetworkLegend'
import { NetworkLoading } from './NetworkLoading'
import { EmptyNetworkState } from './EmptyNetworkState'
import { NetworkTableView } from './NetworkTableView'
import type { RiskBand, AmlPattern } from '@/types'

// Lazy-load the heavy canvas component (D3 inside)
const NetworkCanvas = lazy(() =>
  import('./NetworkCanvas').then(m => ({ default: m.NetworkCanvas }))
)

export const TransactionNetwork: React.FC = () => {
  const report    = useReportStore((s) => s.report)
  const openDrawer = useUiStore((s) => s.openDrawer)

  // ── Graph data — memoised, adapter pattern ────────────────────────
  const graphData = useMemo(
    () => buildGraphData(report ?? MOCK_EXECUTION_REPORT),
    [report]
  )

  // ── Filter state ──────────────────────────────────────────────────
  const [activeRisk,    setActiveRisk]    = useState<RiskBand | 'all'>('all')
  const [activePattern, setActivePattern] = useState<AmlPattern | 'all'>('all')
  const [searchQuery,   setSearchQuery]   = useState('')
  const [selectedId,    setSelectedId]    = useState<string | null>(null)
  const [tableView,     setTableView]     = useState(false)

  // Filtered graph data (memoised)
  const filteredData = useMemo(
    () => filterGraphData(graphData, { riskBand: activeRisk, pattern: activePattern }),
    [graphData, activeRisk, activePattern]
  )

  // ── Zoom / reset refs ─────────────────────────────────────────────
  const onResetRef  = useRef<(() => void) | null>(null)

  const handleZoomIn  = useCallback(() => { /* zoom handled by D3 inside canvas */ }, [])
  const handleZoomOut = useCallback(() => { /* zoom handled by D3 inside canvas */ }, [])
  const handleReset   = useCallback(() => onResetRef.current?.(), [])

  // Click node → open existing EntityDrawer (reuses existing screen ④)
  const handleSelectNode = useCallback((id: string) => {
    setSelectedId(id)
    openDrawer(id)
  }, [openDrawer])

  // Empty state
  if (graphData.nodes.length === 0) {
    return (
      <div className="panel flex flex-col">
        <NetworkHeader count={0} />
        <EmptyNetworkState />
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.2, 0, 0, 1] }}
      className="panel flex flex-col gap-0 overflow-hidden"
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-border-hairline shrink-0">
        <div className="flex items-center gap-2">
          <Network size={13} className="text-accent-cyan" aria-hidden />
          <span className="text-xs font-semibold text-text-primary">
            Entity Risk Network
          </span>
          <span className="text-[10px] font-mono text-text-secondary">
            {filteredData.stats.totalNodes} nodes · {filteredData.stats.edgeCount} edges
          </span>
        </div>
        <NetworkSearch value={searchQuery} onChange={setSearchQuery} />
      </div>

      {/* ── Filter bar ── */}
      <div className="px-4 py-2.5 border-b border-border-hairline/50 shrink-0">
        <NetworkFilters
          patterns={graphData.patterns}
          activePattern={activePattern}
          onPattern={setActivePattern}
          activeRisk={activeRisk}
          onRisk={setActiveRisk}
        />
      </div>

      {/* ── Main body ── */}
      <div className="flex flex-1 min-h-[360px]">
        {/* Canvas / table area */}
        <div className="flex-1 relative">
          {tableView ? (
            <div className="overflow-auto h-full">
              <NetworkTableView
                nodes={filteredData.nodes}
                selectedId={selectedId}
                onSelect={handleSelectNode}
              />
            </div>
          ) : (
            <Suspense fallback={<NetworkLoading />}>
              <NetworkCanvas
                data={filteredData}
                selectedId={selectedId}
                searchQuery={searchQuery}
                onSelectNode={handleSelectNode}
                zoomIn={handleZoomIn}
                zoomOut={handleZoomOut}
                onResetRef={onResetRef}
              />
            </Suspense>
          )}
        </div>

        {/* Right sidebar: controls + legend */}
        <div className="flex flex-col gap-4 px-3 py-3 border-l border-border-hairline shrink-0 w-[140px]">
          <NetworkControls
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onReset={handleReset}
            onToggleView={() => setTableView(v => !v)}
            tableView={tableView}
          />
          <div className="divider" aria-hidden />
          <NetworkLegend patterns={graphData.patterns} />
        </div>
      </div>

      {/* ── Footer: edge explanation ── */}
      <div className="px-4 py-2 border-t border-border-hairline/50 shrink-0">
        <p className="text-[10px] text-text-secondary/70">
          Edges connect customers co-flagged for the same AML pattern in this detection run.
          Click any node to open the Entity Deep-Dive.
        </p>
      </div>
    </motion.div>
  )
}

// ── Small helper ─────────────────────────────────────────────────────
const NetworkHeader: React.FC<{ count: number }> = ({ count }) => (
  <div className="flex items-center gap-2 px-4 py-3 border-b border-border-hairline shrink-0">
    <Network size={13} className="text-accent-cyan" aria-hidden />
    <span className="text-xs font-semibold text-text-primary">Entity Risk Network</span>
    <span className="text-[10px] font-mono text-text-secondary">{count} nodes</span>
  </div>
)
