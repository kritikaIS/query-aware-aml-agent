/**
 * Loader — full-screen or inline loading state
 */

import React from 'react'
import { cn } from '@/utils'
import { Spinner } from './Spinner'

interface LoaderProps {
  fullScreen?: boolean
  message?: string
  className?: string
}

export const Loader: React.FC<LoaderProps> = ({
  fullScreen = false,
  message,
  className,
}) => (
  <div
    className={cn(
      'flex flex-col items-center justify-center gap-3',
      fullScreen && 'fixed inset-0 bg-bg-void z-overlay',
      !fullScreen && 'p-8',
      className
    )}
    role="status"
    aria-live="polite"
  >
    <Spinner size="lg" />
    {message && (
      <p className="text-sm text-text-secondary">{message}</p>
    )}
  </div>
)
