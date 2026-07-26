/**
 * Drawer — slides in from right over dimmed backdrop
 * Documented Requirement: §5.4 Entity Deep-Dive drawer, §7.1 motion-base slide-in
 * §10: Esc key closes, focus management
 */

import React, { useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { cn } from '@/utils'
import { drawerVariants, backdropVariants } from '@/animations'

interface DrawerProps {
  open: boolean
  onClose: () => void
  title?: React.ReactNode
  children: React.ReactNode
  className?: string
  /** Width class, e.g. 'w-96' or 'max-w-md' */
  width?: string
}

export const Drawer: React.FC<DrawerProps> = ({
  open,
  onClose,
  title,
  children,
  className,
  width = 'w-[420px]',
}) => {
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  // Esc closes (§10)
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  // Focus close button on open (§10)
  useEffect(() => {
    if (open) {
      setTimeout(() => closeButtonRef.current?.focus(), 50)
    }
  }, [open])

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Dimmed backdrop (§5.4) */}
          <motion.div
            key="drawer-backdrop"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            className="fixed inset-0 bg-black/50 z-drawer"
            onClick={onClose}
            aria-hidden
          />

          {/* Drawer panel */}
          <motion.aside
            key="drawer-panel"
            role="complementary"
            aria-label={typeof title === 'string' ? title : 'Detail panel'}
            variants={drawerVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className={cn(
              'fixed top-0 right-0 h-full z-drawer',
              'bg-bg-panel border-l border-border-hairline',
              'flex flex-col overflow-hidden',
              width,
              className
            )}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-border-hairline shrink-0">
              {title && (
                <div className="text-text-primary font-semibold">
                  {title}
                </div>
              )}
              <button
                ref={closeButtonRef}
                onClick={onClose}
                className="ml-auto p-1.5 rounded-md text-text-secondary hover:text-text-primary transition-colors focus-visible:outline-accent-cyan"
                aria-label="Close panel"
              >
                <X size={16} />
              </button>
            </div>

            {/* Scrollable body */}
            <div className="flex-1 overflow-y-auto p-6">
              {children}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
