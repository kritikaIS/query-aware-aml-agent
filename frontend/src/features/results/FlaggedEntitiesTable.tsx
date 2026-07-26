/**
 * FlaggedEntitiesTable — §5.3 Results Dashboard
 * Documented Requirements:
 * - Sortable entity list
 * - Each row: risk badge · customer ID · score · AML pattern · action ▸
 * - Every row expands inline (accordion) before deep-dive drawer
 * - Donut cross-filter applied here
 * §10: keyboard navigable table; role="table" with proper ARIA
 */

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { EntityRow } from '@/components/aml'
import { useReducedMotion } from '@/hooks'
import type { FlaggedEntity } from '@/types'

interface FlaggedEntitiesTableProps {
  entities:      FlaggedEntity[]
  onOpenDrawer?: (customerId: string) => void
}

export const FlaggedEntitiesTable: React.FC<FlaggedEntitiesTableProps> = ({
  entities,
  onOpenDrawer,
}) => {
  const reduced = useReducedMotion()

  if (entities.length === 0) {
    return (
      <div className="panel py-8 text-center text-sm text-text-secondary">
        No entities match the current filter.
      </div>
    )
  }

  return (
    <div
      role="table"
      aria-label="Flagged entities"
      className="panel overflow-hidden"
    >
      {/* Fix #26: Table header must NOT be aria-hidden — column labels are needed by AT.
          Using role="rowgroup" + role="columnheader" for proper semantic table structure. */}
      <div role="rowgroup">
        <div role="row" className="flex items-center gap-3 px-4 py-2 border-b border-border-hairline bg-bg-panel-raised">
          <span role="columnheader" className="w-16 text-[10px] font-semibold text-text-secondary uppercase tracking-wider shrink-0">Risk</span>
          <span role="columnheader" className="w-28 text-[10px] font-semibold text-text-secondary uppercase tracking-wider shrink-0">Customer</span>
          <span role="columnheader" className="w-16 text-[10px] font-semibold text-text-secondary uppercase tracking-wider shrink-0">Score</span>
          <span role="columnheader" className="flex-1 text-[10px] font-semibold text-text-secondary uppercase tracking-wider">Pattern</span>
          <span role="columnheader" className="hidden tablet:flex w-28 text-[10px] font-semibold text-text-secondary uppercase tracking-wider shrink-0">Action</span>
          <span role="columnheader" className="w-12 shrink-0" aria-label="Expand" />
        </div>
      </div>

      {/* Rows */}
      <div role="rowgroup">
        <AnimatePresence initial={false}>
          {entities.map((entity, idx) => (
            <motion.div
              key={entity.customer_id}
              role="row"
              layout="position"
              initial={reduced ? undefined : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0, transition: { duration: 0.18, delay: idx * 0.04 } }}
              exit={reduced ? undefined : { opacity: 0, transition: { duration: 0.15 } }}
            >
              <EntityRow
                entity={entity}
                onOpenDrawer={onOpenDrawer}
                isFirst={idx === 0}
                isLast={idx === entities.length - 1}
              />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
