/**
 * Formatting utilities
 * All values are read from ExecutionReport — frontend never computes (§12).
 * These functions only FORMAT for display, never calculate.
 */

/**
 * Format a risk score (0–1) as a percentage string for display.
 * e.g. 0.87 → "0.87"  (kept as decimal — matches backend schema §8)
 */
export function formatScore(score: number): string {
  return score.toFixed(2)
}

/**
 * Format a large number with locale-aware thousands separators.
 * e.g. 48213 → "48,213"
 */
export function formatCount(n: number): string {
  return n.toLocaleString('en-US')
}

/**
 * Format a currency amount.
 * e.g. 9800 → "$9,800"
 */
export function formatCurrency(amount: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(amount)
}

/**
 * Format a z-score for feature bars.
 * e.g. 3.1 → "z=3.1"
 */
export function formatZScore(z: number): string {
  return `z=${z.toFixed(1)}`
}

/**
 * Format an ISO timestamp for display.
 * e.g. "2026-07-24T14:30:00Z" → "Jul 24, 14:30"
 */
export function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

/**
 * Truncate a string to maxLength with ellipsis.
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength - 1) + '…'
}

/**
 * Convert snake_case feature name to a human-readable label.
 * e.g. "near_threshold_txn_count_7d" → "Near Threshold Txn Count 7d"
 */
export function featureLabel(name: string): string {
  return name
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}
