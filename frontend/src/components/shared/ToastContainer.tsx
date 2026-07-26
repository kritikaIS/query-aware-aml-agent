/**
 * ToastContainer — renders error/warning toasts from uiStore
 * Surfaces API errors, backend failures, and mock fallback notices
 * to the user without blocking the UI.
 * §10: aria-live="polite" for screen reader announcements
 */

import React, { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, AlertCircle, CheckCircle, AlertTriangle, Info } from 'lucide-react'
import { useUiStore } from '@/stores'
import { cn } from '@/utils'
import type { ToastType } from '@/types'

const TOAST_ICONS: Record<ToastType, React.ReactNode> = {
  error:   <AlertCircle  size={14} aria-hidden />,
  warning: <AlertTriangle size={14} aria-hidden />,
  success: <CheckCircle  size={14} aria-hidden />,
  info:    <Info         size={14} aria-hidden />,
}

const TOAST_CLASSES: Record<ToastType, string> = {
  error:   'border-risk-high/40   bg-risk-high/10   text-risk-high',
  warning: 'border-risk-medium/40 bg-risk-medium/10 text-risk-medium',
  success: 'border-risk-low/40    bg-risk-low/10    text-risk-low',
  info:    'border-accent-cyan/40 bg-accent-cyan/10 text-accent-cyan',
}

const AUTO_DISMISS_MS: Record<ToastType, number> = {
  error:   8000,
  warning: 6000,
  success: 3000,
  info:    4000,
}

export const ToastContainer: React.FC = () => {
  const toasts      = useUiStore((s) => s.toasts)
  const removeToast = useUiStore((s) => s.removeToast)

  return (
    // Fix #43: removed aria-live from container — each toast item has role="alert"
    // which is sufficient. Nested aria-live causes duplicate SR announcements.
    <div
      className="fixed bottom-4 right-4 z-tooltip flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      aria-label="Notifications"
    >
      <AnimatePresence initial={false}>
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            id={toast.id}
            type={toast.type}
            message={toast.message}
            duration={toast.duration ?? AUTO_DISMISS_MS[toast.type]}
            onDismiss={removeToast}
          />
        ))}
      </AnimatePresence>
    </div>
  )
}

// ── Individual toast ──────────────────────────────────────────────────
interface ToastItemProps {
  id:        string
  type:      ToastType
  message:   string
  duration:  number
  onDismiss: (id: string) => void
}

const ToastItem: React.FC<ToastItemProps> = ({
  id, type, message, duration, onDismiss,
}) => {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(id), duration)
    return () => clearTimeout(timer)
  }, [id, duration, onDismiss])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0,  scale: 1    }}
      exit={{    opacity: 0, y: 8,  scale: 0.96 }}
      transition={{ duration: 0.18, ease: [0.2, 0, 0, 1] }}
      className={cn(
        'pointer-events-auto flex items-start gap-2.5 px-3.5 py-3',
        'rounded-lg border shadow-raised',
        'bg-bg-panel',   // override individual type bg for legibility
        TOAST_CLASSES[type],
      )}
      role="alert"
      aria-live="assertive"
    >
      <span className="mt-0.5 shrink-0">{TOAST_ICONS[type]}</span>
      <span className="text-xs text-text-primary flex-1 leading-snug">{message}</span>
      <button
        type="button"
        onClick={() => onDismiss(id)}
        className="shrink-0 p-0.5 text-text-secondary hover:text-text-primary transition-colors"
        aria-label="Dismiss notification"
      >
        <X size={12} aria-hidden />
      </button>
    </motion.div>
  )
}
