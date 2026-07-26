/**
 * JsonInspector — Screen ⑥ Raw JSON Inspector (Slide-over)
 * Documented Requirement: §5.5
 * "A monospace, syntax-highlighted, collapsible tree view of the exact
 * ExecutionReport object (Solution Design §8) behind everything the judge
 * just saw — one click from anywhere in the app."
 *
 * §3: "slide-over" overlay — judge never loses their place
 * §11: Uses react-json-view themed to §4 palette
 * §6: <JsonTree> states: collapsed/expanded per node. Search + copy-path on hover
 *
 * Animations:
 * - Slide from right: drawerVariants (x:'100%'→0, motion-base 300ms) §7.1
 * - Backdrop fade: backdropVariants §7.1
 * - Toolbar entrance: fade in after slide (motion-fast 180ms) §7.1
 *
 * §10 Accessibility:
 * - role="dialog" aria-modal aria-labelledby
 * - Esc closes, focus trap, focus restoration
 * - Copy action announces via aria-live
 *
 * §9 Responsive:
 * - Desktop: w-[580px] — wider than EntityDrawer to show JSON comfortably
 * - Tablet:  w-[480px]
 * - Mobile:  full width
 *
 * §12 Data flow: reads reportStore.report verbatim — no computation
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X, Code2 } from 'lucide-react'
import { useUiStore, useReportStore } from '@/stores'
import { useReducedMotion } from '@/hooks'
import { drawerVariants, backdropVariants } from '@/animations'
import { cn } from '@/utils'
import { JsonToolbar } from './JsonToolbar'
import { JsonBreadcrumb } from './JsonBreadcrumb'
import { JsonViewer } from './JsonViewer'
import { MOCK_EXECUTION_REPORT } from '@/features/results/mock'
import { MOTION } from '@/constants'

export const JsonInspector: React.FC = () => {
  const open                 = useUiStore((s) => s.jsonInspectorOpen)
  const setOpen              = useUiStore((s) => s.setJsonInspectorOpen)
  const report               = useReportStore((s) => s.report)
  const reduced              = useReducedMotion()

  // §12: render the same ExecutionReport verbatim
  const jsonData = report ?? MOCK_EXECUTION_REPORT

  // Toolbar state
  const [searchQuery,    setSearchQuery]    = useState('')
  const [expandSignal,   setExpandSignal]   = useState(0)
  const [collapseSignal, setCollapseSignal] = useState(0)
  const [selectedPath,   setSelectedPath]   = useState<string[]>([])

  // Focus management refs (§10)
  const triggerRef     = useRef<HTMLElement | null>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const panelRef       = useRef<HTMLElement>(null)

  const close = useCallback(() => setOpen(false), [setOpen])

  // Capture trigger + restore focus (§10)
  useEffect(() => {
    if (open) {
      triggerRef.current = document.activeElement as HTMLElement
      setTimeout(() => closeButtonRef.current?.focus(), 60)
    } else {
      setTimeout(() => triggerRef.current?.focus(), 50)
    }
  }, [open])

  // Keyboard trap + Esc (§10)
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        close()
        return
      }
      if (e.key === 'Tab') {
        const panel = panelRef.current
        if (!panel) return
        const focusable = panel.querySelectorAll<HTMLElement>(
          'button, input, [href], [tabindex]:not([tabindex="-1"])'
        )
        const first = focusable[0]
        const last  = focusable[focusable.length - 1]
        if (e.shiftKey) {
          if (document.activeElement === first) { e.preventDefault(); last?.focus() }
        } else {
          if (document.activeElement === last) { e.preventDefault(); first?.focus() }
        }
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, close])

  // Raw JSON string for copy button
  const rawJson = JSON.stringify(jsonData, null, 2)

  // Content stagger
  const contentVariants = {
    hidden:  { opacity: 0, y: reduced ? 0 : 8 },
    visible: {
      opacity: 1, y: 0,
      transition: { duration: reduced ? 0 : MOTION.FAST, ease: [0.2, 0, 0, 1] as [number,number,number,number] },
    },
  }
  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: reduced ? 0 : 0.04,
        delayChildren:   reduced ? 0 : 0.1,
      },
    },
  }

  const headingId = 'json-inspector-heading'

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* ── Backdrop (§5.5 slide-over) ── */}
          <motion.div
            key="json-backdrop"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            className="fixed inset-0 bg-black/50 z-drawer"
            onClick={close}
            aria-hidden
          />

          {/* ── Slide-over panel ── */}
          <motion.aside
            key="json-inspector"
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={headingId}
            variants={drawerVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className={cn(
              'fixed top-0 right-0 h-full z-drawer',
              'bg-bg-panel border-l border-border-hairline',
              'flex flex-col overflow-hidden',
              // §9: Mobile full-width, tablet 480px, desktop 580px
              'w-full tablet:w-[480px] desktop:w-[580px]',
            )}
          >
            {/* ── Header ── */}
            <motion.div
              variants={contentVariants}
              initial="hidden"
              animate="visible"
              className="flex items-center gap-3 px-5 py-4 border-b border-border-hairline shrink-0"
            >
              <Code2 size={14} className="text-accent-violet shrink-0" aria-hidden />
              <h2
                id={headingId}
                className="text-sm font-semibold text-text-primary flex-1"
              >
                Raw JSON Inspector
              </h2>
              <span className="text-[10px] font-mono text-text-secondary hidden tablet:inline">
                ExecutionReport
              </span>
              {/* ✕ Close */}
              <button
                ref={closeButtonRef}
                type="button"
                onClick={close}
                aria-label="Close JSON inspector"
                className={cn(
                  'p-1.5 rounded-md text-text-secondary hover:text-text-primary',
                  'transition-colors duration-[100ms]',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-cyan',
                )}
              >
                <X size={15} aria-hidden />
              </button>
            </motion.div>

            {/* ── Toolbar ── */}
            <motion.div
              variants={contentVariants}
              initial="hidden"
              animate="visible"
              className="px-5 py-3 border-b border-border-hairline shrink-0 bg-bg-panel-raised/40"
            >
              <JsonToolbar
                onExpandAll={()   => setExpandSignal(s => s + 1)}
                onCollapseAll={() => setCollapseSignal(s => s + 1)}
                searchQuery={searchQuery}
                onSearch={setSearchQuery}
                rawJson={rawJson}
              />
            </motion.div>

            {/* ── Breadcrumb ── */}
            <motion.div
              variants={contentVariants}
              initial="hidden"
              animate="visible"
              className="px-5 py-2 border-b border-border-hairline/50 shrink-0 min-h-[32px]"
              aria-live="polite"
              aria-label="Selected node path"
            >
              <JsonBreadcrumb path={selectedPath} />
            </motion.div>

            {/* ── JSON tree (scrollable) ── */}
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              className="flex-1 overflow-y-auto px-5 py-4"
            >
              {/* Schema hint */}
              <motion.div variants={contentVariants} className="mb-4">
                <div className="flex items-center gap-2 text-[10px] font-mono text-text-secondary/70">
                  <span className="text-accent-cyan">ExecutionReport</span>
                  <span>·</span>
                  <span>Solution Design §8</span>
                  <span>·</span>
                  <span>{Object.keys(jsonData).length} top-level keys</span>
                </div>
              </motion.div>

              {/* §5.5: "monospace, syntax-highlighted, collapsible tree view" */}
              <motion.div variants={contentVariants}>
                <JsonViewer
                  data={jsonData as unknown as object}
                  collapsed={2}
                  expandSignal={expandSignal}
                  collapseSignal={collapseSignal}
                  searchQuery={searchQuery}
                  onSelectPath={setSelectedPath}
                />
              </motion.div>
            </motion.div>

            {/* ── Footer: byte count / trust signal ── */}
            <motion.div
              variants={contentVariants}
              initial="hidden"
              animate="visible"
              className="px-5 py-2.5 border-t border-border-hairline shrink-0"
            >
              <p className="text-[10px] font-mono text-text-secondary/60">
                {rawJson.length.toLocaleString()} chars ·{' '}
                <span className="text-accent-cyan/70">
                  every value on-screen traces to a key in this payload
                </span>
              </p>
            </motion.div>

          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
