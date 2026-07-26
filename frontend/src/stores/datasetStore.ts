/**
 * Dataset Store — dataset status shown in top bar (§5.1)
 * Documented Requirement: Dataset status pill pulled live from Data Loader Tool (§5.1)
 */

import { create } from 'zustand'
import type { DatasetStatus } from '@/types'

interface DatasetState {
  status: DatasetStatus
  setStatus: (status: DatasetStatus) => void
  setLoaded: (rowCount: number, freshness: string) => void
  reset: () => void
}

const INITIAL_STATUS: DatasetStatus = {
  loaded: false,
  rowCount: null,
  freshness: null,
}

export const useDatasetStore = create<DatasetState>((set) => ({
  status: INITIAL_STATUS,
  setStatus: (status) => set({ status }),
  setLoaded: (rowCount, freshness) =>
    set({ status: { loaded: true, rowCount, freshness } }),
  reset: () => set({ status: INITIAL_STATUS }),
}))
