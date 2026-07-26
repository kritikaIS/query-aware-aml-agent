/**
 * App root — SPA state-driven routing
 * Documented Requirement: §3 single-page, state-driven (no route changes mid-query)
 * Query Console → Plan Visualizer → Results Dashboard is one continuous animated
 * sequence driven by AppView state in uiStore.
 *
 * Hardening fixes:
 * - Removed dead PlaceholderView component (issue #2)
 * - Merged duplicate imports from @/features/query (issue #1)
 * - Added ErrorBoundary around each screen to prevent full app crash (issue #3/#55)
 */

import { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AppShell } from '@/layouts'
import { TopBar, ToastContainer } from '@/components/shared'
import { QueryConsole, MOCK_DATASET_STATUS } from '@/features/query'
import { PlanVisualizer } from '@/features/plan'
import { ResultsDashboard } from '@/features/results'
import { EntityDrawer } from '@/features/drawer'
import { JsonInspector } from '@/features/inspector'
import { useUiStore, useDatasetStore } from '@/stores'
import { pageVariants } from '@/animations'
import { ErrorBoundary } from '@/components/ui'

export default function App() {
  const currentView = useUiStore((s) => s.currentView)
  const setLoaded   = useDatasetStore((s) => s.setLoaded)

  useEffect(() => {
    if (MOCK_DATASET_STATUS.loaded && MOCK_DATASET_STATUS.rowCount && MOCK_DATASET_STATUS.freshness) {
      setLoaded(MOCK_DATASET_STATUS.rowCount, MOCK_DATASET_STATUS.freshness)
    }
  }, [setLoaded])

  return (
    <AppShell topBar={<TopBar />}>
      <AnimatePresence mode="wait">
        <motion.div
          key={currentView}
          variants={pageVariants}
          initial="enter"
          animate="center"
          exit="exit"
          className="flex-1 flex flex-col"
        >
          {/* Each screen is wrapped in its own ErrorBoundary so a render error
              in one screen doesn't crash the entire app (fix #3/#55). */}
          {currentView === 'query' && (
            <ErrorBoundary name="Query Console">
              <QueryConsole />
            </ErrorBoundary>
          )}
          {currentView === 'plan' && (
            <ErrorBoundary name="Plan Visualizer">
              <PlanVisualizer />
            </ErrorBoundary>
          )}
          {currentView === 'results' && (
            <ErrorBoundary name="Results Dashboard">
              <ResultsDashboard />
            </ErrorBoundary>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Overlays — outside AnimatePresence so they persist across view transitions */}
      <ErrorBoundary name="Entity Drawer">
        <EntityDrawer />
      </ErrorBoundary>

      <ErrorBoundary name="JSON Inspector">
        <JsonInspector />
      </ErrorBoundary>

      <ToastContainer />
    </AppShell>
  )
}
