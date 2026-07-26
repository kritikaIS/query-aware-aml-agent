/**
 * NetworkCanvas — D3 force-directed graph rendered on SVG
 * Documented Requirement: §8 "Smurfing network graph (stretch) — D3 force-directed"
 *
 * All D3 imports are lazy (dynamic import inside useEffect) so they never
 * appear in the initial bundle (§13 performance budget).
 *
 * Node encoding:
 *   radius     ∝ risk_score  (§ Step 5)
 *   fill color ← risk_band   (§4.1 colors)
 *   glow       ← selected node (§ Step 5)
 *
 * Edge encoding:
 *   Only between nodes sharing the same aml_pattern_matched (§ adapter.ts)
 *   Color matches the §4.1 accent tokens
 *
 * Interactions:
 *   click   → openDrawer(customer_id)
 *   hover   → show EntityTooltip
 *   drag    → pin node (d.fx/d.fy)
 *   zoom    → SVG viewBox transform
 *   pan     → SVG viewBox transform
 *
 * §10 Reduced motion: force simulation still runs but layout transitions
 *   are instant (no animated ticks visible to user)
 * §9 Responsive: canvas fills its container, re-simulates on resize
 */

import React, {
  useRef, useEffect, useState, useMemo,
} from 'react'
import { useReducedMotion } from '@/hooks'
import { EntityTooltip } from './EntityTooltip'
import type { GraphData, GraphNode } from './adapter'

// ── Design token colour values ────────────────────────────────────────
const NODE_COLOR: Record<string, string> = {
  High:   '#F0473C',  // --risk-high
  Medium: '#F5B93D',  // --risk-medium
  Low:    '#2FBF71',  // --risk-low
}
const NODE_SELECTED = '#3ED6C4'  // --accent-cyan
const EDGE_COLOR    = 'rgba(62,214,196,0.25)'  // --accent-cyan/25
const BG_COLOR      = '#0A0E14'  // --bg-void

interface NetworkCanvasProps {
  data:           GraphData
  selectedId:     string | null
  searchQuery:    string
  onSelectNode:   (id: string) => void
  zoomIn:         () => void
  zoomOut:        () => void
  onResetRef:     React.MutableRefObject<(() => void) | null>
}

interface TooltipState {
  node: GraphNode
  x:    number
  y:    number
}

export const NetworkCanvas: React.FC<NetworkCanvasProps> = ({
  data,
  selectedId,
  searchQuery,
  onSelectNode,
  onResetRef,
}) => {
  // Fix #33: ref so D3 event handlers always call the latest onSelectNode,
  // avoiding the stale closure that occurs when D3 captures the prop at init time.
  const onSelectNodeRef = useRef(onSelectNode)
  useEffect(() => { onSelectNodeRef.current = onSelectNode }, [onSelectNode])

  const svgRef      = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const reduced    = useReducedMotion()

  const [tooltip,   setTooltip]   = useState<TooltipState | null>(null)
  const [canvasSize, setCanvasSize] = useState({ w: 600, h: 400 })

  // Focus node matching search query
  const focusedId = useMemo(() => {
    if (!searchQuery.trim()) return null
    const q = searchQuery.trim().toLowerCase()
    return data.nodes.find(n => n.id.toLowerCase().includes(q))?.id ?? null
  }, [data.nodes, searchQuery])

  // Initialise D3 force simulation — lazy import
  useEffect(() => {
    if (!svgRef.current || data.nodes.length === 0) return
    const svg = svgRef.current

    // Clear previous content
    while (svg.firstChild) svg.removeChild(svg.firstChild)

    const { w, h } = canvasSize

    let cleanup: (() => void) | undefined

    // Dynamic import keeps D3 out of the initial bundle
    // Fix #34: check mounted flag before setting up simulation/DOM after async import
    let mounted = true
    Promise.all([
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore — D3 sub-packages resolve at runtime; types unavailable at compile time for dynamic imports
      import('d3-force'),
      // @ts-ignore
      import('d3-selection'),
      // @ts-ignore
      import('d3-zoom'),
      // @ts-ignore
      import('d3-drag'),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ]).then(([d3Force, d3Sel, d3Zoom, d3Drag]: any[]) => {
      if (!mounted) return
      // Deep-clone nodes so D3 can mutate x/y without dirtying our store data
      const nodes: GraphNode[] = data.nodes.map(n => ({ ...n }))
      const nodeById = new Map(nodes.map(n => [n.id, n]))

      // D3 mutates source/target to resolved node objects — cast to any for compatibility
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const edges: any[] = data.edges.map(e => ({
        ...e,
        source: nodeById.get(e.source) ?? e.source,
        target: nodeById.get(e.target) ?? e.target,
      }))

      // ── SVG root ──────────────────────────────────────────────────
      const d3svg = d3Sel.select(svg)
        .attr('width',  w)
        .attr('height', h)
        .attr('aria-label', 'Entity risk network graph')
        .attr('role', 'img')

      // Background fill
      d3svg.append('rect')
        .attr('width',  w)
        .attr('height', h)
        .attr('fill',   BG_COLOR)

      // Container group for zoom/pan
      const g = d3svg.append('g').attr('class', 'network-root')

      // ── Zoom behaviour ────────────────────────────────────────────
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const zoom = (d3Zoom.zoom as any)()
        .scaleExtent([0.25, 4])
        .on('zoom', (event: { transform: unknown }) => {
          g.attr('transform', event.transform)
        })

      d3svg.call(zoom)

      // Expose reset to parent
      onResetRef.current = () => {
        d3svg.transition().duration(400).call(
          zoom.transform,
          d3Zoom.zoomIdentity.translate(w / 2, h / 2).scale(0.85)
        )
      }

      // Initial centering
      d3svg.call(
        zoom.transform,
        d3Zoom.zoomIdentity.translate(w / 2, h / 2).scale(0.85)
      )

      // ── Force simulation ──────────────────────────────────────────
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const simulation = d3Force.forceSimulation(nodes as any[])
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .force('link', d3Force.forceLink(edges as any[])
          .id((d: unknown) => (d as GraphNode).id)
          .distance(90)
          .strength(0.4))
        .force('charge', d3Force.forceManyBody().strength(-220))
        .force('center', d3Force.forceCenter(0, 0))
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .force('collide', (d3Force.forceCollide as any)().radius((d: GraphNode) => d.radius + 6))
        .alphaDecay(0.03)

      // ── Edges ─────────────────────────────────────────────────────
      const link = g.append('g').attr('class', 'links')
        .selectAll('line')
        .data(edges)
        .join('line')
        .attr('stroke',         EDGE_COLOR)
        .attr('stroke-width',   1.5)
        .attr('stroke-linecap', 'round')

      // ── Nodes ─────────────────────────────────────────────────────
      const nodeGroup = g.append('g').attr('class', 'nodes')
        .selectAll('g')
        .data(nodes)
        .join('g')
        .attr('class',        'node-group')
        .attr('cursor',       'pointer')
        .attr('tabindex',     0)
        .attr('role',         'button')
        .attr('aria-label',   (d: GraphNode) => `Customer ${d.id}, ${d.risk_band} risk, score ${d.risk_score.toFixed(2)}`)

      // Glow filter for selected node
      const defs = d3svg.append('defs')
      const filter = defs.append('filter').attr('id', 'node-glow')
      filter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur')
      const feMerge = filter.append('feMerge')
      feMerge.append('feMergeNode').attr('in', 'blur')
      feMerge.append('feMergeNode').attr('in', 'SourceGraphic')

      // Outer glow ring (selected state)
      nodeGroup.append('circle')
        .attr('class', 'node-glow-ring')
        .attr('r', (d: GraphNode) => d.radius + 5)
        .attr('fill',    'none')
        .attr('stroke',   NODE_SELECTED)
        .attr('stroke-width', 1.5)
        .attr('opacity', (d: GraphNode) => d.id === selectedId ? 0.7 : 0)
        .attr('filter',  'url(#node-glow)')

      // Main node circle
      nodeGroup.append('circle')
        .attr('class', 'node-circle')
        .attr('r',     (d: GraphNode) => d.radius)
        .attr('fill',  (d: GraphNode) =>
          d.id === selectedId ? NODE_SELECTED : NODE_COLOR[d.risk_band] ?? '#888'
        )
        .attr('stroke',       'rgba(255,255,255,0.12)')
        .attr('stroke-width', 1)
        .attr('opacity',      (d: GraphNode) => {
          if (focusedId && d.id !== focusedId) return 0.3
          return 1
        })

      // Customer ID label
      nodeGroup.append('text')
        .attr('class',      'node-label')
        .attr('text-anchor','middle')
        .attr('dy',         '0.35em')
        .attr('fill',       '#E8ECF4')
        .attr('font-size',  10)
        .attr('font-family','JetBrains Mono, monospace')
        .attr('pointer-events', 'none')
        .attr('opacity',    (d: GraphNode) => d.radius >= 12 ? 1 : 0)
        .text((d: GraphNode) => d.id)

      // ── Drag ──────────────────────────────────────────────────────
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const drag = (d3Drag.drag as any)()
        .on('start', (event: { active: boolean; x: number; y: number }, d: GraphNode) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event: { x: number; y: number }, d: GraphNode) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event: { active: boolean }, d: GraphNode) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        })

      nodeGroup.call(drag as never)

      // ── Interactions ──────────────────────────────────────────────
      nodeGroup
        .on('click', (_event: unknown, d: GraphNode) => {
          onSelectNodeRef.current(d.id)
        })
        .on('keydown', (event: KeyboardEvent, d: GraphNode) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            onSelectNodeRef.current(d.id)
          }
        })
        .on('mouseenter', (event: MouseEvent, d: GraphNode) => {
          const rect = svg.getBoundingClientRect()
          setTooltip({
            node: d,
            x:    event.clientX - rect.left,
            y:    event.clientY - rect.top,
          })
        })
        .on('mousemove', (event: MouseEvent, d: GraphNode) => {
          const rect = svg.getBoundingClientRect()
          setTooltip({
            node: d,
            x:    event.clientX - rect.left,
            y:    event.clientY - rect.top,
          })
        })
        .on('mouseleave', () => setTooltip(null))

      // ── Tick ──────────────────────────────────────────────────────
      const tickCount = reduced ? 300 : 0  // run synchronously if reduced motion

      if (reduced) {
        // Run all ticks synchronously — no visible animation
        for (let i = 0; i < tickCount; i++) simulation.tick()
        // Apply final positions
        link
          .attr('x1', (d: unknown) => ((d as { source: GraphNode }).source.x ?? 0))
          .attr('y1', (d: unknown) => ((d as { source: GraphNode }).source.y ?? 0))
          .attr('x2', (d: unknown) => ((d as { target: GraphNode }).target.x ?? 0))
          .attr('y2', (d: unknown) => ((d as { target: GraphNode }).target.y ?? 0))
        nodeGroup.attr('transform', (d: GraphNode) => `translate(${d.x ?? 0},${d.y ?? 0})`)
      } else {
        simulation.on('tick', () => {
          link
            .attr('x1', (d: unknown) => ((d as { source: GraphNode }).source.x ?? 0))
            .attr('y1', (d: unknown) => ((d as { source: GraphNode }).source.y ?? 0))
            .attr('x2', (d: unknown) => ((d as { target: GraphNode }).target.x ?? 0))
            .attr('y2', (d: unknown) => ((d as { target: GraphNode }).target.y ?? 0))
          nodeGroup.attr('transform', (d: GraphNode) => `translate(${d.x ?? 0},${d.y ?? 0})`)
        })
      }

      cleanup = () => {
        simulation.stop()
      }
    })

    return () => {
      mounted = false
      cleanup?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, canvasSize, selectedId, focusedId, reduced])

  // Observe container size — debounced to prevent D3 re-simulation on every resize pixel (fix #35)
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    let debounceId: ReturnType<typeof setTimeout>
    const ro = new ResizeObserver(entries => {
      const e = entries[0]
      if (e) {
        clearTimeout(debounceId)
        debounceId = setTimeout(() => {
          setCanvasSize({ w: e.contentRect.width, h: e.contentRect.height })
        }, 100)
      }
    })
    ro.observe(el)
    return () => {
      clearTimeout(debounceId)
      ro.disconnect()
    }
  }, [])

  return (
    <div ref={containerRef} className="relative flex-1 w-full min-h-[320px]">
      <svg
        ref={svgRef}
        className="w-full h-full rounded-lg overflow-hidden"
        aria-label="Entity risk network. Use Tab to navigate nodes, Enter to open detail."
      />
      {tooltip && (
        <EntityTooltip
          node={tooltip.node}
          x={tooltip.x}
          y={tooltip.y}
          width={canvasSize.w}
          height={canvasSize.h}
        />
      )}
    </div>
  )
}
