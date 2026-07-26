/**
 * JsonViewer — the core react-json-view component, themed to §4 palette
 * Documented Requirement: §11 "JSON tree / inspector: react-json-view (themed to match §4 palette)"
 * §5.5: "monospace, syntax-highlighted, collapsible tree view"
 * §4.2: JetBrains Mono for all JSON content
 * §6: <JsonTree> states: collapsed/expanded per node
 *
 * Hardening fixes applied:
 * - setState-during-render anti-pattern replaced with useEffect (issue #31)
 * - Unsafe `as number` cast guarded with type check (issue #32)
 */

import React, { lazy, Suspense, useEffect, useState } from 'react'
import { cn } from '@/utils'

// Proven runtime shape (see diagnostic output):
//   import('react-json-view') → m = { default: require_main() }
//   m.default = CJS exports object t = { __esModule: true, default: Be, ... }
//   m.default.default = Be = the actual React PureComponent class
// React.lazy requires { default: ComponentType }, so we extract m.default.default.
const ReactJson = lazy(() =>
  import('react-json-view').then((m: unknown) => {
    const mod = m as { default: { default: React.ComponentType<unknown> } }
    return { default: mod.default.default }
  })
)

interface JsonViewerProps {
  data:            object
  collapsed?:      boolean | number
  expandSignal?:   number
  collapseSignal?: number
  searchQuery?:    string
  onSelectPath?:   (path: string[]) => void
}

const JSON_THEME = {
  base00: 'transparent',
  base01: 'var(--bg-panel-raised)',
  base02: 'var(--border-hairline)',
  base03: 'var(--text-secondary)',
  base04: 'var(--text-secondary)',
  base05: 'var(--text-primary)',
  base06: 'var(--text-primary)',
  base07: 'var(--text-primary)',
  base08: 'var(--risk-high)',
  base09: '#F5B93D',
  base0A: 'var(--risk-medium)',
  base0B: '#2FBF71',
  base0C: 'var(--accent-cyan)',
  base0D: 'var(--accent-cyan)',
  base0E: 'var(--accent-violet)',
  base0F: 'var(--text-secondary)',
}

export const JsonViewer: React.FC<JsonViewerProps> = ({
  data,
  collapsed = 1,
  expandSignal,
  collapseSignal,
  searchQuery = '',
  onSelectPath,
}) => {
  const [internalCollapsed, setInternalCollapsed] = useState<boolean | number>(collapsed)

  // Fix #31: use useEffect instead of setting state during render body.
  // This avoids the infinite-loop / render-order violation.
  useEffect(() => {
    if (expandSignal !== undefined) {
      setInternalCollapsed(false)
    }
  }, [expandSignal])

  useEffect(() => {
    if (collapseSignal !== undefined) {
      setInternalCollapsed(true)
    }
  }, [collapseSignal])

  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-32">
        <div className="text-xs font-mono text-text-secondary animate-pulse">
          Loading JSON viewer…
        </div>
      </div>
    }>
      <div
        className={cn(
          'json-viewer-container',
          '[&_.react-json-view]:!font-mono [&_.react-json-view]:!text-xs',
          '[&_.react-json-view]:!bg-transparent',
        )}
        aria-label="JSON tree viewer"
      >
        <ReactJson
          src={data}
          theme={JSON_THEME}
          name={false}
          collapsed={internalCollapsed}
          displayDataTypes={false}
          displayObjectSize={true}
          enableClipboard={(copy) => {
            if (onSelectPath && copy.namespace) {
              navigator.clipboard.writeText(copy.namespace.join('.')).catch(() => {})
            }
            return true
          }}
          onSelect={(select) => {
            if (onSelectPath && select.namespace) {
              onSelectPath([...select.namespace.map(String), String(select.name)])
            }
          }}
          style={{
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize:   '12px',
            lineHeight: '1.7',
            background: 'transparent',
            padding:    0,
          }}
          shouldCollapse={searchQuery
            ? (field) => {
                const nameStr  = String(field.name ?? '')
                const valueStr = typeof field.src === 'object' ? '' : String(field.src ?? '')
                const q        = searchQuery.toLowerCase()
                if (nameStr.toLowerCase().includes(q))  return false
                if (valueStr.toLowerCase().includes(q)) return false
                // Fix #32: guard before numeric cast
                if (typeof internalCollapsed === 'boolean') return internalCollapsed
                if (typeof internalCollapsed === 'number') {
                  return field.type === 'object' || field.type === 'array'
                    ? field.namespace.length >= internalCollapsed
                    : false
                }
                return false
              }
            : undefined
          }
        />
      </div>
    </Suspense>
  )
}
