/**
 * Report Store — ExecutionReport and derived UI state
 * Documented Requirement: Zustand for report state (§11, §12)
 * Single source of truth — frontend never derives numbers (§12).
 */

import { create } from 'zustand'
import type { ExecutionReport, FlaggedEntity, RiskFilter, SortConfig } from '@/types'

interface ReportState {
  // The raw ExecutionReport payload — never mutated, always authoritative (§12)
  report: ExecutionReport | null
  setReport: (report: ExecutionReport) => void

  // Cross-filter: which risk band is selected in the donut (§5.3)
  riskFilter: RiskFilter
  setRiskFilter: (filter: RiskFilter) => void

  // Sort config for flagged entities table (§5.3 "sort: risk ▾")
  sortConfig: SortConfig
  setSortConfig: (config: SortConfig) => void

  // Derived: filtered + sorted entities (computed on read, not stored)
  getFilteredEntities: () => FlaggedEntity[]

  reset: () => void
}

export const useReportStore = create<ReportState>((set, get) => ({
  report: null,
  setReport: (report) => set({ report }),

  riskFilter: 'all',
  setRiskFilter: (filter) => set({ riskFilter: filter }),

  sortConfig: { field: 'risk_score', direction: 'desc' },
  setSortConfig: (config) => set({ sortConfig: config }),

  getFilteredEntities: () => {
    const { report, riskFilter, sortConfig } = get()
    if (!report) return []

    let entities = [...report.flagged_entities]

    // Apply risk filter (donut click cross-filter, §5.3)
    if (riskFilter !== 'all') {
      entities = entities.filter((e) => e.risk_band === riskFilter)
    }

    // Apply sort
    entities.sort((a, b) => {
      const aVal = a[sortConfig.field as keyof FlaggedEntity]
      const bVal = b[sortConfig.field as keyof FlaggedEntity]
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortConfig.direction === 'desc' ? bVal - aVal : aVal - bVal
      }
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortConfig.direction === 'desc'
          ? bVal.localeCompare(aVal)
          : aVal.localeCompare(bVal)
      }
      return 0
    })

    return entities
  },

  reset: () =>
    set({
      report: null,
      riskFilter: 'all',
      sortConfig: { field: 'risk_score', direction: 'desc' },
    }),
}))
