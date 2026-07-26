import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/globals.css'

// ── Global error capture for verification testing ─────────────────────
// Stores every error into localStorage['__aml_errors'] as JSON array.
// ErrorBoundary.componentDidCatch also logs to console.error.
const _errors: Array<{ type: string; message: string; stack?: string; component?: string }> = []

window.addEventListener('error', (e) => {
  _errors.push({ type: 'uncaught', message: e.message, stack: e.error?.stack })
  localStorage.setItem('__aml_errors', JSON.stringify(_errors))
})

window.addEventListener('unhandledrejection', (e: PromiseRejectionEvent) => {
  const msg = e.reason instanceof Error ? e.reason.message : String(e.reason)
  const stack = e.reason instanceof Error ? e.reason.stack : undefined
  _errors.push({ type: 'unhandledRejection', message: msg, stack })
  localStorage.setItem('__aml_errors', JSON.stringify(_errors))
})

// Expose for programmatic inspection
;(window as unknown as Record<string, unknown>).__aml_errors = _errors

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
