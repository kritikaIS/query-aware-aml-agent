/**
 * NetworkLoading — loading state while D3 initialises
 */
import React from 'react'
import { motion } from 'framer-motion'

export const NetworkLoading: React.FC = () => (
  <div className="flex-1 flex flex-col items-center justify-center gap-4 min-h-[320px]">
    <motion.div
      animate={{ opacity: [0.4, 1, 0.4] }}
      transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
      className="flex gap-2"
    >
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="size-2 rounded-full bg-accent-cyan"
          style={{ animationDelay: `${i * 0.3}s` }}
        />
      ))}
    </motion.div>
    <p className="text-xs text-text-secondary font-mono">
      Building entity network…
    </p>
  </div>
)
