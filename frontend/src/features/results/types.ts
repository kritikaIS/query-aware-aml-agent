/** Local types for Results feature (re-exported from mock) */

export interface HistogramBin {
  bin:   string
  count: number
}

export interface TimelinePoint {
  date:           string
  amount:         number
  customer_id:    string
  flagged:        boolean
  near_threshold: boolean
}
