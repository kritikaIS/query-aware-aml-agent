/**
 * ThresholdHistogram — §6 Component Library
 * Documented Requirement: §8 "Amount distribution histogram (Plotly)"
 * Key encoding: "Vertical reference line at $10,000 with label, always visible"
 * §8 design contract: axis labels in --text-secondary; hover tooltip cites source
 * §11: Plotly.js for histogram/scatter
 */

import React, { lazy, Suspense } from 'react'

// Lazy-load Plotly (§13 bundle budget)
// react-plotly.js is CJS/UMD; Vite pre-bundles it as:
//   export default require_react_plotly()
// require_react_plotly() returns the CJS exports object { __esModule: true, default: PlotlyComponent }.
// React.lazy requires { default: ComponentType }, so we must extract m.default.default.
const Plot = lazy(() =>
  import('react-plotly.js').then((m: unknown) => {
    const mod = m as { default: { default: React.ComponentType<unknown> } }
    return { default: mod.default.default }
  })
)

interface HistogramBin {
  bin:   string
  count: number
}

interface ThresholdHistogramProps {
  data: HistogramBin[]
}

// Plotly layout config using CSS variable values (§4.1)
const LAYOUT = {
  paper_bgcolor: 'transparent',
  plot_bgcolor:  'transparent',
  margin:        { t: 8, r: 12, b: 40, l: 44 },
  font:          { family: 'Inter, system-ui', size: 11, color: '#8B98B4' },
  xaxis: {
    tickfont:     { size: 10, color: '#8B98B4' },
    tickangle:    -30,
    showgrid:     false,
    showline:     true,
    linecolor:    '#232D42',
    fixedrange:   true,
  },
  yaxis: {
    tickfont:  { size: 10, color: '#8B98B4' },
    showgrid:  true,
    gridcolor: '#232D42',
    showline:  false,
    fixedrange: true,
  },
  // §8: vertical reference line at $10,000 "always visible"
  shapes: [
    {
      type:      'line' as const,
      x0:        6.5,     // between "$9.5k–$10k" and "$10k+" bins (0-indexed)
      x1:        6.5,
      y0:        0,
      y1:        1,
      yref:      'paper' as const,
      line:      { color: '#F5B93D', width: 1.5, dash: 'dash' as const },
    },
  ],
  annotations: [
    {
      x:          6.5,
      y:          1,
      yref:       'paper' as const,
      text:       '$10k threshold',
      showarrow:  false,
      font:       { size: 10, color: '#F5B93D' },
      xanchor:    'left' as const,
      yanchor:    'top'  as const,
      xshift:     6,
    },
  ],
  showlegend: false,
}

const CONFIG = {
  displayModeBar:  false,
  responsive:      true,
  staticPlot:      false,
}

export const ThresholdHistogram: React.FC<ThresholdHistogramProps> = ({ data }) => {
  const trace = {
    type:        'bar' as const,
    x:           data.map(d => d.bin),
    y:           data.map(d => d.count),
    marker: {
      color:     data.map((_, i) =>
        // Highlight near-threshold bins (bins 5 and 6, $9k–$10k) in amber
        i >= 5 && i <= 6 ? '#F5B93D' : '#3ED6C4'
      ),
      opacity: 0.85,
    },
    hovertemplate: '<b>%{x}</b><br>%{y} transactions<extra></extra>',
  }

  return (
    <Suspense fallback={
      <div className="w-full h-48 rounded bg-bg-panel-raised animate-pulse flex items-center justify-center">
        <span className="text-xs text-text-secondary">Loading chart…</span>
      </div>
    }>
      <div className="w-full h-48" aria-label="Amount distribution histogram with $10,000 reporting threshold line">
        <Plot
          data={[trace]}
          layout={LAYOUT}
          config={CONFIG}
          style={{ width: '100%', height: '100%' }}
          useResizeHandler
        />
      </div>
    </Suspense>
  )
}
