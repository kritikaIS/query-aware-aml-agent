/**
 * Mock data for the Query Console screen.
 * Implementation Assumption: mocked dataset metadata (task brief).
 * When backend is connected, this is replaced by a live /health call.
 */

import type { DatasetStatus } from '@/types'

export const MOCK_DATASET_STATUS: DatasetStatus = {
  loaded:    true,
  rowCount:  48213,      // matches §8 summary_metrics.total_transactions_scanned example
  freshness: 'Jul 25, 2026',
}
