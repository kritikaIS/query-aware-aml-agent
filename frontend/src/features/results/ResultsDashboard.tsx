/**
 * ResultsDashboard — Screen ③
 * Documented Requirement: §5.3 Risk Report Dashboard
 *
 * Layout (§5.3 wireframe):
 *  ┌─────────────────────────────────────────────────────────────┐
 *  │ ◂ Query recap · plan summary · [View raw JSON ⧉]             │
 *  │                                                               │
 *  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐  │
 *  │  │ 48,213       │ │ 17           │ │  3🔴 9🟡 5🟢 (donut) │  │
 *  │  │ txns scanned │ │ entities     │ │  risk split           │  │
 *  │  └──────────────┘ └──────────────┘ └──────────────────────┘  │
 *  │                                                               │
 *  │  Flagged Entities                      sort: risk ▾          │
 *  │  [table with accordion rows]                                  │
 *  │                                                               │
 *  │  ┌─────────────────────┐  ┌──────────────────────────────┐  │
 *  │  │ Amount distribution  │  │ Flagged activity timeline     │  │
 *  │  └─────────────────────┘  └──────────────────────────────┘  │
 *  └─────────────────────────────────────────────────────────────┘
 *
 * §9 Responsive:
 *   Desktop ≥1280px: KPI tiles 3-column, charts 2-column
 *   Tablet 768–1279px: KPI tiles 2×2, charts single column
 *   Mobile: single column all sections
 *
 * Animations:
 *   §7.2 Seq 3: RiskBadge score-resolve (400ms) — in EntityRow
 *   §7.2 Seq 4: KPI count-up (600ms, mount-only) — in KpiTile
 *   §7.1 motion-slow: chart entrance (500ms)
 *   §7.1 motion-base: dashboard section stagger
 */

import React from 'react'
import { motion } from 'framer-motion'
import { useReportStore, useUiStore } from '@/stores'
import { useReducedMotion } from '@/hooks'
import { KpiTile, RiskDonut, DonutLegend } from '@/components/aml'
import { SummaryHeader } from './SummaryHeader'
import { FilterBar } from './FilterBar'
import { FlaggedEntitiesTable } from './FlaggedEntitiesTable'
import { MetricsRail } from './MetricsRail'
import { MOCK_EXECUTION_REPORT, MOCK_HISTOGRAM_DATA, MOCK_TIMELINE_DATA } from './mock'
import { MOTION } from '@/constants'
import { TransactionNetwork } from '@/features/network'

export const ResultsDashboard: React.FC = () => {
  const reduced = useReducedMotion()

  // §12: report is populated by useQuery hook via reportStore.setReport(report)
  // No mock seeding here — the real ExecutionReport from POST /query is the source.
  // Mock fallback is handled in useQuery when the backend is unreachable.
  const report = useReportStore((s) => s.report)

  // ── Read all display data from store (§12: never compute numbers) ──
  const riskFilter    = useReportStore((s) => s.riskFilter)
  const setRiskFilter = useReportStore((s) => s.setRiskFilter)
  const sortConfig    = useReportStore((s) => s.sortConfig)
  const setSortConfig = useReportStore((s) => s.setSortConfig)
  const getFiltered   = useReportStore((s) => s.getFilteredEntities)
  const openDrawer    = useUiStore((s) => s.openDrawer)

  const filteredEntities = getFiltered()
  const metrics          = report?.summary_metrics ?? MOCK_EXECUTION_REPORT.summary_metrics
  const plan             = report?.execution_plan  ?? MOCK_EXECUTION_REPORT.execution_plan

  const toolsInvoked = plan.steps.length
  const toolsSkipped = plan.skipped_tools.length

  // ── Page stagger container ──────────────────────────────────────────
  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: reduced ? 0 : 0.07,
        delayChildren:   0,
      },
    },
  }

  const sectionVariants = {
    hidden:  { opacity: 0, y: reduced ? 0 : 14 },
    visible: {
      opacity: 1, y: 0,
      transition: {
        duration: reduced ? 0 : MOTION.BASE,
        ease: [0.2, 0, 0, 1] as [number, number, number, number],
      },
    },
  }

  return (
    // Fix #16: removed duplicate role="main" — AppShell already provides <main>
    <div className="flex-1 flex flex-col px-4 tablet:px-6 desktop:px-8 py-6 desktop:py-8 gap-6">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="w-full max-w-[1200px] mx-auto flex flex-col gap-6"
      >

        {/* ── Summary header (§5.3 "◂ Query recap · [View raw JSON ⧉]") ── */}
        <motion.div variants={sectionVariants}>
          <SummaryHeader
            query={report?.user_query ?? MOCK_EXECUTION_REPORT.user_query}
            toolsInvoked={toolsInvoked}
            toolsSkipped={toolsSkipped}
          />
        </motion.div>

        {/* ── KPI tiles row (§5.3, §7.2 Seq 4 count-up) ────────────── */}
        {/* §9: Desktop: 3-col · Tablet: 2-col (KpiTile goes 2×2) · Mobile: 1-col */}
        <motion.div variants={sectionVariants}>
          <div className="grid grid-cols-1 tablet:grid-cols-2 desktop:grid-cols-3 gap-4">

            {/* KPI 1: Transactions scanned */}
            <KpiTile
              value={metrics.total_transactions_scanned}
              label="txns scanned"
              sublabel="in filtered window"
            />

            {/* KPI 2: Entities flagged */}
            <KpiTile
              value={metrics.entities_flagged}
              label="entities flagged"
              sublabel={`across all risk bands`}
            />

            {/* KPI 3: Risk split with donut — §5.3 "3 🔴 9 🟡 5 🟢 (donut)" */}
            {/* §9: On tablet this tile takes 2 cols to span the row cleanly */}
            <div className="panel p-5 tablet:col-span-2 desktop:col-span-1">
              <div className="flex items-center gap-4 h-full">
                {/* Donut chart (§8 RiskDonut, Recharts) */}
                <RiskDonut
                  metrics={metrics}
                  activeFilter={riskFilter}
                  onFilter={setRiskFilter}
                  size={88}
                />
                {/* Legend + click-filter controls */}
                <div className="flex flex-col gap-1 min-w-0 flex-1">
                  <span className="text-xs font-medium text-text-secondary uppercase tracking-wider mb-1">
                    Risk split
                  </span>
                  <DonutLegend
                    metrics={metrics}
                    activeFilter={riskFilter}
                    onFilter={setRiskFilter}
                  />
                </div>
              </div>
            </div>

          </div>
        </motion.div>

        {/* ── Flagged Entities Table (§5.3) ────────────────────────── */}
        <motion.div variants={sectionVariants}>
          <div className="flex flex-col gap-3">
            <FilterBar
              sortConfig={sortConfig}
              onSortChange={setSortConfig}
              entityCount={metrics.entities_flagged}
              filteredCount={filteredEntities.length}
              activeFilter={riskFilter}
            />
            <FlaggedEntitiesTable
              entities={filteredEntities}
              onOpenDrawer={(id) => openDrawer(id)}
            />
          </div>
        </motion.div>

        {/* ── Charts rail (§5.3, §8) ──────────────────────────────── */}
        <motion.div variants={sectionVariants}>
          <MetricsRail
            histogramData={MOCK_HISTOGRAM_DATA}
            timelineData={MOCK_TIMELINE_DATA}
          />
        </motion.div>

        {/* ── Entity Risk Network (§8 "Smurfing network graph, stretch") ── */}
        {/* Completely independent feature — reads from reportStore */}
        <motion.div variants={sectionVariants}>
          <TransactionNetwork />
        </motion.div>

      </motion.div>
    </div>
  )
}
