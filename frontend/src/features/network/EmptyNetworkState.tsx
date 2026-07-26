/**
 * EmptyNetworkState — shown when there are no entities to visualise
 */
import React from 'react'
import { Network } from 'lucide-react'

interface EmptyNetworkStateProps {
  message?: string
}

export const EmptyNetworkState: React.FC<EmptyNetworkStateProps> = ({
  message = 'No flagged entities to visualise. Run a query to see the network.',
}) => (
  <div className="flex-1 flex flex-col items-center justify-center gap-3 min-h-[320px]">
    <Network size={32} className="text-border-hairline" aria-hidden />
    <p className="text-sm text-text-secondary text-center max-w-xs leading-relaxed">
      {message}
    </p>
  </div>
)
