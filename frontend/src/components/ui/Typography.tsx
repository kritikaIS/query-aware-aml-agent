/**
 * Typography — semantic text components
 * Documented Requirement: §4.2 sans-serif = system talking to you,
 * monospace = raw fact you can verify.
 */

import React from 'react'
import { cn } from '@/utils'

// ── Heading ──────────────────────────────────────────────────────────
interface HeadingProps extends React.HTMLAttributes<HTMLHeadingElement> {
  level?: 1 | 2 | 3 | 4
}

const headingSizes = { 1: 'text-3xl', 2: 'text-2xl', 3: 'text-xl', 4: 'text-lg' }

export const Heading: React.FC<HeadingProps> = ({ level = 2, className, children, ...props }) => {
  const Tag = `h${level}` as 'h1' | 'h2' | 'h3' | 'h4'
  return (
    <Tag
      className={cn(
        'font-semibold text-text-primary leading-tight',
        headingSizes[level],
        className
      )}
      {...props}
    >
      {children}
    </Tag>
  )
}

// ── Body text ──────────────────────────────────────────────────────────
interface TextProps extends React.HTMLAttributes<HTMLParagraphElement> {
  variant?: 'primary' | 'secondary' | 'caption'
  size?: 'sm' | 'base' | 'md'
}

const textVariants = {
  primary:   'text-text-primary',
  secondary: 'text-text-secondary',
  caption:   'text-text-secondary text-xs',
}

const textSizes = { sm: 'text-sm', base: 'text-base', md: 'text-md' }

export const Text: React.FC<TextProps> = ({
  variant = 'primary',
  size = 'base',
  className,
  children,
  ...props
}) => (
  <p className={cn(textVariants[variant], textSizes[size], className)} {...props}>
    {children}
  </p>
)

// ── Monospace value (machine-generated — §4.2) ────────────────────────
interface MonoProps extends React.HTMLAttributes<HTMLSpanElement> {
  size?: 'xs' | 'sm' | 'base'
}

const monoSizes = { xs: 'text-xs', sm: 'text-sm', base: 'text-base' }

export const Mono: React.FC<MonoProps> = ({
  size = 'sm',
  className,
  children,
  ...props
}) => (
  <span
    className={cn('font-mono text-text-primary', monoSizes[size], className)}
    data-value="machine"
    {...props}
  >
    {children}
  </span>
)

// ── Label ─────────────────────────────────────────────────────────────
export const Label: React.FC<React.HTMLAttributes<HTMLSpanElement>> = ({
  className,
  children,
  ...props
}) => (
  <span
    className={cn('text-xs font-medium text-text-secondary uppercase tracking-wider', className)}
    {...props}
  >
    {children}
  </span>
)
