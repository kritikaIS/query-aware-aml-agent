/**
 * CustomerMetadata — customer profile metadata row
 * Documented Requirement: §5.4 header area
 * Displays: Customer ID · AML Pattern · Risk band
 * §4.2: customer ID in monospace (machine-generated value)
 */

import React from 'react'
import { cn } from '@/utils'
import type { AmlPattern, RiskBand } from '@/types'

interface CustomerMetadataProps {
  customerId:  string
  amlPattern:  AmlPattern
  riskBand:    RiskBand
}

const PATTERN_LABEL: Record<string, string> = {
  structuring:   'Structuring',
  smurfing:      'Smurfing',
  layering:      'Layering',
  rapid_cashout: 'Rapid Cash-Out',
}

export const CustomerMetadata: React.FC<CustomerMetadataProps> = ({
  customerId,
  amlPattern,
  riskBand,
}) => {
  const patternLabel = amlPattern ? (PATTERN_LABEL[amlPattern] ?? amlPattern) : null

  return (
    <div className="flex flex-col gap-3">
      {/* Customer ID — monospace (§4.2) */}
      <div>
        <p className="text-[11px] text-text-secondary font-medium uppercase tracking-wider">
          Customer ID
        </p>
        <p className="text-2xl font-bold font-mono text-text-primary mt-0.5">
          {customerId}
        </p>
      </div>

      {/* Pattern + band metadata row */}
      <div className="flex flex-wrap gap-2">
        {/* Risk band pill */}
        <span className={cn(
          'inline-flex items-center gap-1 text-xs font-mono font-medium px-2 py-0.5 rounded-full border',
          riskBand === 'High'   && 'text-risk-high   bg-risk-high/10   border-risk-high/30',
          riskBand === 'Medium' && 'text-risk-medium bg-risk-medium/10 border-risk-medium/30',
          riskBand === 'Low'    && 'text-risk-low    bg-risk-low/10   border-risk-low/30',
        )}>
          ● {riskBand}
        </span>

        {/* AML pattern pill */}
        {patternLabel && (
          <span className="inline-flex items-center gap-1 text-xs font-mono text-text-primary bg-bg-panel-raised px-2 py-0.5 rounded-full border border-border-hairline">
            {patternLabel}
          </span>
        )}
      </div>

      {/* Matched pattern label (§5.4 "Matched pattern: structuring") */}
      {amlPattern && (
        <div className="flex items-center gap-1.5 text-xs text-text-secondary">
          <span className="font-medium">Matched pattern:</span>
          <span className="font-mono text-text-primary">{amlPattern}</span>
        </div>
      )}
    </div>
  )
}
