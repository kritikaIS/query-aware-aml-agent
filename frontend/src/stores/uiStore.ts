/**
 * UI Store — app view state, drawer, modal, toast, JSON inspector
 * Documented Requirement: Zustand for UI state (§11, §12)
 * No business logic — state container only.
 */

import { create } from 'zustand'
import type { AppView, DrawerState, ToastMessage } from '@/types'

interface UiState {
  // Current app view (SPA state machine, §3)
  currentView: AppView
  setView: (view: AppView) => void

  // Entity deep-dive drawer (§5.4)
  drawer: DrawerState
  openDrawer: (entityId: string) => void
  closeDrawer: () => void

  // Raw JSON inspector open/close (§5.5)
  jsonInspectorOpen: boolean
  setJsonInspectorOpen: (open: boolean) => void

  // Toast notifications
  toasts: ToastMessage[]
  addToast: (toast: Omit<ToastMessage, 'id'>) => void
  removeToast: (id: string) => void

  // "Skip to results" — judge can jump past plan animation at any time (§7.3)
  skipToResults: boolean
  setSkipToResults: (skip: boolean) => void
}

export const useUiStore = create<UiState>((set) => ({
  currentView: 'query',
  setView: (view) => set({ currentView: view }),

  drawer: { open: false, entityId: null },
  openDrawer: (entityId) =>
    set({ drawer: { open: true, entityId } }),
  closeDrawer: () =>
    set({ drawer: { open: false, entityId: null } }),

  jsonInspectorOpen: false,
  setJsonInspectorOpen: (open) => set({ jsonInspectorOpen: open }),

  toasts: [],
  addToast: (toast) => {
    // Fix #12: use crypto.randomUUID() for deterministic, collision-free IDs
    const id = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `toast-${Date.now()}-${Math.random()}`
    set((s) => ({ toasts: [...s.toasts, { ...toast, id }] }))
  },
  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  skipToResults: false,
  setSkipToResults: (skip) => set({ skipToResults: skip }),
}))
