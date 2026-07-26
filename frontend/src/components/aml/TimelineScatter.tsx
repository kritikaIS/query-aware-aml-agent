/**
 * TimelineScatter — §6 Component Library
 * Documented Requirement: §8 "Flagged activity timeline (scatter, D3/Plotly)"
 * Key encoding:
 *   "Point size = transaction amount"
 *   "Near-threshold points get a subtle halo"
 * §8 design contract: axis labels --text-secondary; hover tooltip cites source
 * §11: Plotly.js for scatter
 */

import React, { lazy, Suspense } from 'react'

// react-plotly.js is CJS/UMD; Vite pre-bundles it as:
//   export default require_react_plotly()
// require_react_plotly() returns the CJS exports object { __esModule: true, default: PlotlyComponent }.
// React.lazy requires { default: ComponentType }, so we must extract m.default.default.
// Cast to React.FC<any> to avoid TS errors on JSX props — the runtime type is correct.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const Plot = lazy(() =>
  import('react-plotly.js').then((m: unknown) => {
    const mod = m as { default: { default: React.ComponentType<any> } }
    return { default: mod.default.default }
  })
)

interface TimelinePoint {
  date:          string
  amount:        number
  customer_id:   string
  flagged:       boolean
  near_threshold: boolean
}

interface TimelineScatterProps {
  data: TimelinePoint[]
}

const LAYOUT = {
  paper_bgcolor: 'transparent',
  plot_bgcolor:  'transparent',
  margin:        { t: 8, r: 12, b: 40, l: 44 },
  font:          { family: 'Inter, system-ui', size: 11, color: '#8B98B4' },
  xaxis: {
    tickfont:   { size: 10, color: '#8B98B4' },
    showgrid:   false,
    showline:   true,
    linecolor:  '#232D42',
    type:       'date' as const,
    fixedrange: true,
  },
  yaxis: {
    tickfont:   { size: 10, color: '#8B98B4' },
    showgrid:   true,
    gridcolor:  '#232D42',
    showline:   false,
    title:      { text: 'Amount ($)', font: { size: 10, color: '#8B98B4' } },
    fixedrange: true,
  },
  // $10k reference line — consistent with histogram (§8)
  shapes: [
    {
      type:    'line' as const,
      x0:      0, x1:  1, xref: 'paper' as const,
      y0:      10000, y1: 10000,
      line:    { color: '#F5B93D', width: 1, dash: 'dot' as const },
    },
  ],
  showlegend: false,
}

const CONFIG = {
  displayModeBar: false,
  responsive:     true,
}

export const TimelineScatter: React.FC<TimelineScatterProps> = ({ data }) => {
  // §8: near-threshold points get halo (rendered as second trace with larger, low-opacity marker)
  const nearThreshold = data.filter(d => d.near_threshold)
  const allPoints     = data

  // Halo trace for near-threshold points
  const haloTrace = {
    type:  'scatter' as const,
    mode:  'markers' as const,
    x:     nearThreshold.map(d => d.date),
    y:     nearThreshold.map(d => d.amount),
    marker: {
      size:    nearThreshold.map(d => (d.amount / 2000) + 18),  // larger halo
      color:   'rgba(240, 71, 60, 0.12)',
      line:    { color: 'rgba(240, 71, 60, 0.3)', width: 1 },
    },
    hoverinfo: 'skip' as const,
    showlegend: false,
  }

  // Main scatter trace — point size = transaction amount (§8)
  const mainTrace = {
    type:  'scatter' as const,
    mode:  'markers' as const,
    x:     allPoints.map(d => d.date),
    y:     allPoints.map(d => d.amount),
    text:  allPoints.map(d => `Customer ${d.customer_id}`),
    marker: {
      size:    allPoints.map(d => Math.max(6, (d.amount / 2000) + 4)),  // §8: size = amount
      color:   allPoints.map(d =>
        d.near_threshold ? '#F0473C' : d.flagged ? '#F5B93D' : '#3ED6C4'
      ),
      opacity: 0.85,
      line:    { color: 'var(--bg-void)', width: 1 },
    },
    hovertemplate: '<b>%{text}</b><br>%{x}<br>$%{y:,.0f}<extra></extra>',
  }

  return (
    <Suspense fallback={
      <div className="w-full h-48 rounded bg-bg-panel-raised animate-pulse flex items-center justify-center">
        <span className="text-xs text-text-secondary">Loading chart…</span>
      </div>
    }>
      <div className="w-full h-48" aria-label="Flagged activity timeline scatter chart">
        <Plot
          data={[haloTrace, mainTrace]}
          layout={LAYOUT}
          config={CONFIG}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler
        />
      </div>
    </Suspense>
  )
}
