/**
 * Card — panel surface with hairline border + inset shadow
 * Documented Requirement: §4.3 panels, glassmorphism minimal rule
 */

import React from 'react'
import { cn } from '@/utils'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  raised?: boolean
  noPadding?: boolean
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ raised = false, noPadding = false, className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        raised ? 'panel-raised' : 'panel',
        !noPadding && 'p-6',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
)

Card.displayName = 'Card'

// Sub-components for composition
export const CardHeader = ({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('mb-4', className)} {...props}>
    {children}
  </div>
)

export const CardBody = ({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('', className)} {...props}>
    {children}
  </div>
)

export const CardFooter = ({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('mt-4 pt-4 divider', className)} {...props}>
    {children}
  </div>
)
