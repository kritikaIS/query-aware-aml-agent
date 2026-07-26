/**
 * UI-specific TypeScript types
 * Implementation Assumption: UI state types not specified in docs;
 * inferred from §5 Screen Specifications and §6 Component Library.
 */

import type { RiskBand, ToolState } from './api'

// ── App-level UI state ──────────────────────────────────────────────
export type AppView = 'query' | 'plan' | 'results'

// ── Tool card display model (§5.2, §6 ToolCard) ─────────────────────
export interface ToolCardModel {
  name: string
  label: string
  state: ToolState
  progress: number      // 0–100
  skipReason?: string   // shown without hover per §5.2
}

// ── Dataset status (§5.1 top bar) ───────────────────────────────────
export interface DatasetStatus {
  loaded: boolean
  rowCount: number | null
  freshness: string | null
}

// ── Risk badge props (§6 RiskBadge) ─────────────────────────────────
export interface RiskBadgeProps {
  band: RiskBand
}

// ── Drawer/modal state ───────────────────────────────────────────────
export interface DrawerState {
  open: boolean
  entityId: string | null
}

// ── Sort direction ───────────────────────────────────────────────────
export type SortDirection = 'asc' | 'desc'

export interface SortConfig {
  field: string
  direction: SortDirection
}

// ── Filter state for risk donut cross-filter (§5.3) ─────────────────
export type RiskFilter = RiskBand | 'all'

// ── Quick-select chip (§5.1) ─────────────────────────────────────────
export interface QuickSelectChip {
  label: string
  query: string
}

// ── Generic component variants ──────────────────────────────────────
export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg'
export type BadgeVariant = 'default' | 'low' | 'medium' | 'high' | 'skipped' | 'active' | 'done' | 'queued' | 'error'

// ── Toast/notification ───────────────────────────────────────────────
export type ToastType = 'info' | 'success' | 'warning' | 'error'

export interface ToastMessage {
  id: string
  type: ToastType
  message: string
  duration?: number
}
