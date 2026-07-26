/**
 * Modal — generic dialog overlay
 * Documented Requirement: §10 keyboard navigable, Esc closes (§5.4)
 * Motion: motion-base slide+fade (§7.1)
 */

import React, { useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { cn } from '@/utils'
import { modalVariants, backdropVariants } from '@/animations'

interface ModalProps {
  open: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  className?: string
  /** Width class, e.g. 'max-w-lg' */
  size?: string
}

export const Modal: React.FC<ModalProps> = ({
  open,
  onClose,
  title,
  children,
  className,
  size = 'max-w-lg',
}) => {
  // Esc key closes modal (§10)
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="modal-backdrop"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            className="fixed inset-0 bg-black/60 z-modal"
            onClick={onClose}
            aria-hidden
          />

          {/* Panel */}
          <div className="fixed inset-0 z-modal flex items-center justify-center p-6 pointer-events-none">
            <motion.div
              key="modal-panel"
              role="dialog"
              aria-modal
              aria-labelledby={title ? 'modal-title' : undefined}
              variants={modalVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className={cn(
                'panel w-full pointer-events-auto',
                size,
                className
              )}
            >
              {title && (
                <div className="flex items-center justify-between mb-4">
                  <h2 id="modal-title" className="text-lg font-semibold text-text-primary">
                    {title}
                  </h2>
                  <button
                    onClick={onClose}
                    className="p-1 rounded-md text-text-secondary hover:text-text-primary transition-colors"
                    aria-label="Close"
                  >
                    <X size={16} />
                  </button>
                </div>
              )}
              {children}
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  )
}
