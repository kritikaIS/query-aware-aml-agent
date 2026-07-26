/**
 * RecommendedActionCard — escalation recommendation row
 * Documented Requirement: §5.4 "Recommended: 🔴 Report (SAR draft)"
 * §5.7 (Solution Design): deterministic policy mapping
 *   Low    → Monitor    → 🟢
 *   Medium → Flag for review → 🟡
 *   High   → Report (SAR draft) → 🔴
 * §10: icon + text + color (never color alone)
 */

import React from 'react'
import { FileText, Eye, Shield, Download } from 'lucide-react'
import { cn } from '@/utils'

interface RecommendedActionCardProps {
  action:     string   // raw recommended_action from ExecutionReport
  riskBand:   string
}

interface ActionConfig {
  icon:       React.ReactNode
  colorClass: string
  bgClass:    string
  borderClass: string
  label:      string
  detail:     string
}

function getActionConfig(action: string): ActionConfig {
  if (action.toLowerCase().includes('report') || action.toLowerCase().includes('sar')) {
    return {
      icon:        <FileText size={14} aria-hidden />,
      colorClass:  'text-risk-high',
      bgClass:     'bg-risk-high/8',
      borderClass: 'border-risk-high/30',
      label:       'Report (SAR draft)',
      detail:      'Auto-draft Suspicious Activity Report for compliance sign-off',
    }
  }
  if (action.toLowerCase().includes('flag') || action.toLowerCase().includes('review')) {
    return {
      icon:        <Eye size={14} aria-hidden />,
      colorClass:  'text-risk-medium',
      bgClass:     'bg-risk-medium/8',
      borderClass: 'border-risk-medium/30',
      label:       'Flag for review',
      detail:      'Analyst review within SLA (3 business days)',
    }
  }
  return {
    icon:        <Shield size={14} aria-hidden />,
    colorClass:  'text-risk-low',
    bgClass:     'bg-risk-low/8',
    borderClass: 'border-risk-low/30',
    label:       'Monitor',
    detail:      'No further action; keep in rolling watch list',
  }
}

export const RecommendedActionCard: React.FC<RecommendedActionCardProps> = ({
  action,
}) => {
  const cfg = getActionConfig(action)

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider">
        Recommended Action
      </p>

      <div
        className={cn(
          'flex items-start justify-between gap-3 px-3 py-3 rounded-lg border',
          cfg.bgClass,
          cfg.borderClass
        )}
      >
        <div className="flex items-start gap-2.5">
          {/* §10: icon + text + color */}
          <span className={cn('mt-0.5 shrink-0', cfg.colorClass)}>
            {cfg.icon}
          </span>
          <div>
            <p className={cn('text-sm font-semibold', cfg.colorClass)}>
              {cfg.label}
            </p>
            <p className="text-xs text-text-secondary mt-0.5 leading-snug">
              {cfg.detail}
            </p>
          </div>
        </div>

        {/* Export button — §5.4 "[Export ⬇]" placeholder */}
        <button
          type="button"
          aria-label="Export entity report (not yet implemented)"
          disabled
          className={cn(
            'inline-flex items-center gap-1 h-7 px-2.5 rounded text-xs font-medium shrink-0',
            'border border-border-hairline text-text-secondary',
            'opacity-50 cursor-not-allowed'
          )}
        >
          <Download size={11} aria-hidden />
          <span className="hidden tablet:inline">Export</span>
        </button>
      </div>
    </div>
  )
}
