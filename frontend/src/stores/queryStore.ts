/**
 * Query Store — current query text and submission state
 * Documented Requirement: Zustand for query state (§11, §12)
 */

import { create } from 'zustand'

type QueryStatus = 'idle' | 'submitting' | 'streaming' | 'complete' | 'error'

interface QueryState {
  queryText: string
  setQueryText: (text: string) => void

  submittedQuery: string | null
  setSubmittedQuery: (query: string) => void

  status: QueryStatus
  setStatus: (status: QueryStatus) => void

  errorMessage: string | null
  setError: (message: string | null) => void

  // Reset back to idle for a new query
  reset: () => void
}

export const useQueryStore = create<QueryState>((set) => ({
  queryText: '',
  setQueryText: (text) => set({ queryText: text }),

  submittedQuery: null,
  setSubmittedQuery: (query) => set({ submittedQuery: query }),

  status: 'idle',
  setStatus: (status) => set({ status }),

  errorMessage: null,
  setError: (message) => set({ errorMessage: message }),

  reset: () =>
    set({
      queryText: '',
      submittedQuery: null,
      status: 'idle',
      errorMessage: null,
    }),
}))
