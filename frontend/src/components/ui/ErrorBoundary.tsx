/**
 * ErrorBoundary — catches render errors and shows a recovery UI.
 * Prevents the entire app from white-screening on an unhandled error in any subtree.
 * Fix for issue #3 / #55.
 */

import React from 'react'
import { AlertCircle } from 'lucide-react'

interface Props {
  children:    React.ReactNode
  /** Identifies the boundary in error reports */
  name?:       string
  /** Custom fallback — defaults to a generic error panel */
  fallback?:   React.ReactNode
}

interface State {
  hasError:   boolean
  message:    string
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error: unknown): State {
    const message =
      error instanceof Error ? error.message : 'An unexpected error occurred.'
    return { hasError: true, message }
  }

  override componentDidCatch(error: unknown, info: React.ErrorInfo) {
    const message = error instanceof Error ? error.message : String(error)
    const stack   = error instanceof Error ? error.stack : undefined
    console.error(
      `[ErrorBoundary${this.props.name ? ` ${this.props.name}` : ''}]`,
      error,
      info.componentStack
    )
    // Write to global error store for programmatic inspection
    try {
      const existing = JSON.parse(localStorage.getItem('__aml_errors') ?? '[]')
      existing.push({
        type:      'ErrorBoundary',
        boundary:  this.props.name ?? 'unknown',
        message,
        stack,
        component: info.componentStack,
      })
      localStorage.setItem('__aml_errors', JSON.stringify(existing))
    } catch { /* ignore storage errors */ }
  }

  handleReset = () => {
    this.setState({ hasError: false, message: '' })
  }

  override render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div className="flex-1 flex items-center justify-center px-6 py-12">
          <div
            role="alert"
            className="panel max-w-md w-full p-6 flex flex-col gap-4"
          >
            <div className="flex items-center gap-2 text-risk-high">
              <AlertCircle size={16} aria-hidden />
              <span className="text-sm font-semibold">
                Something went wrong
                {this.props.name ? ` in ${this.props.name}` : ''}
              </span>
            </div>
            <p className="text-xs text-text-secondary font-mono leading-relaxed">
              {this.state.message}
            </p>
            <button
              type="button"
              onClick={this.handleReset}
              className="text-xs text-accent-cyan hover:underline text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent-cyan rounded"
            >
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
