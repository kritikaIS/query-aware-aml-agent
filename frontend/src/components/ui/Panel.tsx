/**
 * Panel — full-width layout section (different from Card which is a content box)
 * Used as the container for major screen sections.
 */

import React from 'react'
import { cn } from '@/utils'

interface PanelProps extends React.HTMLAttributes<HTMLDivElement> {
  as?: React.ElementType
}

export const Panel = React.forwardRef<HTMLDivElement, PanelProps>(
  ({ as: Tag = 'section', className, children, ...props }, ref) => (
    <Tag
      ref={ref}
      className={cn('panel p-6', className)}
      {...props}
    >
      {children}
    </Tag>
  )
)

Panel.displayName = 'Panel'
