/**
 * REST API client
 * Documented Requirement: POST /query → ExecutionReport (§11, §12)
 * Backend contract: POST /query { query: string } → ExecutionReport JSON (synchronous)
 * Backend: src/api/main.py — single /query endpoint, no SSE streaming
 */

import { API_BASE_URL } from '@/constants'
import type { ExecutionReport, QueryRequest } from '@/types'

// ── Timeouts ──────────────────────────────────────────────────────────
// Backend runs the full pipeline synchronously — allow up to 90s
const QUERY_TIMEOUT_MS  = 90_000
const HEALTH_TIMEOUT_MS = 5_000

// ── Base fetch wrapper ────────────────────────────────────────────────
async function apiFetch<T>(
  path: string,
  options: RequestInit & { timeoutMs?: number } = {}
): Promise<T> {
  const { timeoutMs = 30_000, ...fetchOpts } = options
  const url = `${API_BASE_URL}${path}`

  const controller = new AbortController()
  const timerId    = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...fetchOpts.headers,
      },
      ...fetchOpts,
    })

    if (!res.ok) {
      const errorBody = await res.text().catch(() => '')
      // Parse FastAPI's { detail: string } error shape
      let detail = errorBody
      try {
        const parsed = JSON.parse(errorBody)
        if (parsed.detail) detail = String(parsed.detail)
      } catch { /* use raw text */ }
      throw new ApiError(res.status, res.statusText, detail)
    }

    return res.json() as Promise<T>
  } catch (err) {
    if (err instanceof ApiError) throw err
    if ((err as Error).name === 'AbortError') {
      throw new ApiError(0, 'Timeout', `Request timed out after ${timeoutMs / 1000}s`)
    }
    throw new ApiError(0, 'Network Error', (err as Error).message ?? 'Connection failed')
  } finally {
    clearTimeout(timerId)
  }
}

// ── Custom error type ─────────────────────────────────────────────────
export class ApiError extends Error {
  readonly status: number
  readonly statusText: string
  readonly body: string

  constructor(status: number, statusText: string, body: string) {
    super(`API ${status} ${statusText}: ${body}`)
    this.name = 'ApiError'
    this.status = status
    this.statusText = statusText
    this.body = body
  }

  get userMessage(): string {
    if (this.status === 0)   return this.body   // timeout or network
    if (this.status === 400) return `Bad request: ${this.body}`
    if (this.status === 422) return `Validation error: ${this.body}`
    if (this.status === 500) return `Backend error: ${this.body}`
    return `Request failed (${this.status}): ${this.body}`
  }
}

// ── POST /query (§12 data flow, backend contract: src/api/main.py) ────
// The backend runs the full pipeline synchronously and returns ExecutionReport.
// No SSE stream — the response is a single JSON object.
export async function postQuery(request: QueryRequest): Promise<ExecutionReport> {
  return apiFetch<ExecutionReport>('/query', {
    method:    'POST',
    body:      JSON.stringify(request),
    timeoutMs: QUERY_TIMEOUT_MS,
  })
}

// ── GET /health (backend contract: src/api/main.py /health) ──────────
export interface HealthResponse {
  status:            string
  registered_tools:  string[]
  llm_configured:    boolean
}

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health', { timeoutMs: HEALTH_TIMEOUT_MS })
}
