/**
 * AppShell — root layout
 * Documented Requirement: §3 "App Shell: Top Bar: logo · dataset status ·
 * env indicator · raw-JSON toggle"
 * This is ONLY the layout wrapper. Screen content is rendered by the router.
 * No screens implemented here.
 */

import React from 'react'
import { cn } from '@/utils'

interface AppShellProps {
  topBar?: React.ReactNode
  children: React.ReactNode
  className?: string
}

export const AppShell: React.FC<AppShellProps> = ({ topBar, children, className }) => (
  <div
    className={cn(
      'min-h-screen flex flex-col',
      'bg-bg-void text-text-primary',
      className
    )}
  >
    {/* Top bar slot (§3 App Shell) */}
    {topBar && (
      <header
        className="sticky top-0 z-topbar border-b border-border-hairline bg-bg-panel/95 backdrop-blur-sm"
        role="banner"
      >
        {topBar}
      </header>
    )}

    {/* Main content area */}
    <main className="flex-1 flex flex-col" role="main">
      {children}
    </main>
  </div>
)
