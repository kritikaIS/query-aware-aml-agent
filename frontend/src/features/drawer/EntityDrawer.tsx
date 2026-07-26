/**
 * EntityDrawer — Screen ④ Entity Deep-Dive
 * Documented Requirement: §5.4 Entity Deep-Dive (Drawer)
 *
 * Wireframe (§5.4):
 *  ┌─────────────────────────────┐
 *  │ Customer 4521          ✕    │
 *  │ 🔴 HIGH · score 0.87         │
 *  │                              │
 *  │ Matched pattern: structuring │
 *  │                              │
 *  │ Top contributing features    │
 *  │  near_threshold_txn_count    │
 *  │   6  ▓▓▓▓▓▓▓░░ z=3.1        │
 *  │  avg_amount_deviation        │
 *  │   2.4 ▓▓▓▓▓░░░░ z=2.4       │
 *  │                              │
 *  │ "Customer 4521 made 6..."    │
 *  │                              │
 *  │ Recommended: 🔴 Report        │
 *  └─────────────────────────────┘
 *
 * §3: Overlay/drawer — judge never loses their place in the Results Dashboard
 * §7.1: Drawer slide — motion-base 300ms (uses existing Drawer component)
 * §7.1: Content stagger — sections fade+slide on open
 * §10: role="dialog" aria-modal, focus trap, Esc closes, focus restoration
 * §12: reads from reportStore.report.flagged_entities — no refetch
 *
 * Responsive (§9):
 *  Desktop: w-[460px] right drawer
 *  Tablet:  w-[400px]
 *  Mobile:  full-width bottom sheet OR full-width right drawer
 */

import React, { useRef, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { useUiStore, useReportStore } from '@/stores'
import { useReducedMotion } from '@/hooks'
import { drawerVariants, backdropVariants } from '@/animations'
import { cn } from '@/utils'
import { CustomerMetadata } from '@/components/aml/CustomerMetadata'
import { RiskScoreGauge } from '@/components/aml/RiskScoreGauge'
import { FeatureContributionList } from '@/components/aml/FeatureContributionList'
import { ExplanationPanel } from '@/components/aml/ExplanationPanel'
import { RecommendedActionCard } from '@/components/aml/RecommendedActionCard'
import { MOCK_EXECUTION_REPORT } from '@/features/results/mock'

export const EntityDrawer: React.FC = () => {
  const drawerState  = useUiStore((s) => s.drawer)
  const closeDrawer  = useUiStore((s) => s.closeDrawer)
  const report       = useReportStore((s) => s.report)
  const reduced      = useReducedMotion()

  // Ref to the element that triggered the drawer — for focus restoration (§10)
  const triggerRef      = useRef<HTMLElement | null>(null)
  const closeButtonRef  = useRef<HTMLButtonElement>(null)
  const drawerPanelRef  = useRef<HTMLElement>(null)

  const { open, entityId } = drawerState

  // Find the entity in the report (§12: read from single source of truth)
  const entities    = report?.flagged_entities ?? MOCK_EXECUTION_REPORT.flagged_entities
  const entity      = entityId ? entities.find(e => e.customer_id === entityId) : null

  // Fix #28: store timer IDs and cancel on cleanup to avoid updates after unmount
  useEffect(() => {
    let timerId: ReturnType<typeof setTimeout>
    if (open) {
      triggerRef.current = document.activeElement as HTMLElement
      timerId = setTimeout(() => closeButtonRef.current?.focus(), 60)
    } else {
      timerId = setTimeout(() => triggerRef.current?.focus(), 50)
    }
    return () => clearTimeout(timerId)
  }, [open])

  // ── Keyboard trap (§10) ────────────────────────────────────────────
  useEffect(() => {
    if (!open) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        closeDrawer()
        return
      }

      // Focus trap: keep Tab within the drawer
      if (e.key === 'Tab') {
        const panel     = drawerPanelRef.current
        if (!panel) return
        const focusable = panel.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        const first = focusable[0]
        const last  = focusable[focusable.length - 1]

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault()
            last?.focus()
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault()
            first?.focus()
          }
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, closeDrawer])

  // ── Traced values for explanation annotation (§5.4) ────────────────
  // Numbers that appear in feature bars → underlined in explanation text
  const tracedValues = entity
    ? entity.top_contributing_features.flatMap(f => [f.value, f.z_score])
    : []

  // ── Content stagger variants ────────────────────────────────────────
  const contentContainer = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: reduced ? 0 : 0.06,
        delayChildren:   reduced ? 0 : 0.1,
      },
    },
  }
  const contentSection = {
    hidden:  { opacity: 0, y: reduced ? 0 : 12 },
    visible: {
      opacity: 1, y: 0,
      transition: { duration: reduced ? 0 : 0.25, ease: [0.2, 0, 0, 1] as [number,number,number,number] },
    },
  }

  const headingId = 'entity-drawer-heading'

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* ── Backdrop (§5.4 "dimmed backdrop") ── */}
          <motion.div
            key="entity-backdrop"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            className="fixed inset-0 bg-black/55 z-drawer"
            onClick={closeDrawer}
            aria-hidden
          />

          {/* ── Drawer panel ── */}
          <motion.aside
            key="entity-drawer"
            ref={drawerPanelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={headingId}
            variants={drawerVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className={cn(
              // §9 Responsive widths
              'fixed top-0 right-0 h-full z-drawer',
              'bg-bg-panel border-l border-border-hairline',
              'flex flex-col overflow-hidden',
              // Mobile: full width. Tablet+: fixed width
              'w-full tablet:w-[420px] desktop:w-[460px]',
            )}
          >
            {/* ── Drawer header (§5.4 "Customer 4521 ✕") ── */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border-hairline shrink-0">
              <div>
                {entity ? (
                  <h2
                    id={headingId}
                    className="text-base font-semibold text-text-primary font-mono"
                  >
                    Customer {entity.customer_id}
                  </h2>
                ) : (
                  <h2 id={headingId} className="text-base font-semibold text-text-primary">
                    Entity Detail
                  </h2>
                )}
              </div>

              {/* ✕ Close button */}
              <button
                ref={closeButtonRef}
                type="button"
                onClick={closeDrawer}
                aria-label="Close detail panel"
                className={cn(
                  'p-1.5 rounded-md',
                  'text-text-secondary hover:text-text-primary',
                  'transition-colors duration-[100ms]',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-cyan',
                )}
              >
                <X size={16} aria-hidden />
              </button>
            </div>

            {/* ── Scrollable body ── */}
            <div className="flex-1 overflow-y-auto">
              {entity ? (
                <motion.div
                  variants={contentContainer}
                  initial="hidden"
                  animate="visible"
                  className="flex flex-col gap-6 px-5 py-5"
                >

                  {/* ① Score gauge + customer metadata (§5.4 header section) */}
                  <motion.div variants={contentSection}>
                    <div className="flex items-start gap-4">
                      {/* Animated risk score gauge (§7.2 Seq 3) */}
                      <RiskScoreGauge
                        score={entity.risk_score}
                        band={entity.risk_band}
                      />

                      {/* Customer metadata */}
                      <div className="flex-1 min-w-0">
                        <CustomerMetadata
                          customerId={entity.customer_id}
                          amlPattern={entity.aml_pattern_matched}
                          riskBand={entity.risk_band}
                        />
                      </div>
                    </div>
                  </motion.div>

                  {/* Divider */}
                  <motion.div variants={contentSection} className="divider" aria-hidden />

                  {/* ② Feature contribution bars (§5.4, §8) */}
                  <motion.div variants={contentSection}>
                    <FeatureContributionList
                      features={entity.top_contributing_features}
                    />
                  </motion.div>

                  {/* ③ Explanation paragraph (§5.4 LLM-generated) */}
                  {entity.explanation && (
                    <>
                      <motion.div variants={contentSection} className="divider" aria-hidden />
                      <motion.div variants={contentSection}>
                        <ExplanationPanel
                          explanation={entity.explanation}
                          tracedValues={tracedValues}
                        />
                      </motion.div>
                    </>
                  )}

                  {/* ④ Recommended action (§5.4 "Recommended: 🔴 Report") */}
                  <motion.div variants={contentSection} className="divider" aria-hidden />
                  <motion.div variants={contentSection}>
                    <RecommendedActionCard
                      action={entity.recommended_action}
                      riskBand={entity.risk_band}
                    />
                  </motion.div>

                </motion.div>
              ) : (
                /* Fallback when entity not found */
                <div className="flex items-center justify-center h-40">
                  <p className="text-sm text-text-secondary">Entity not found.</p>
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
