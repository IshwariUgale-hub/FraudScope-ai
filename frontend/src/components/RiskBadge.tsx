import React from 'react'
import { ShieldAlert, ShieldCheck, AlertTriangle } from 'lucide-react'
import type { RiskLevel } from '../types'

interface RiskBadgeProps {
  level: RiskLevel | string
  size?: 'sm' | 'md' | 'lg'
  showIcon?: boolean
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  level,
  size = 'md',
  showIcon = true,
}) => {
  const norm = String(level).toUpperCase()

  const config = {
    LOW: {
      bg: 'bg-emerald-950/70 border-emerald-500/40 text-emerald-400',
      icon: ShieldCheck,
      label: 'LOW RISK',
    },
    MEDIUM: {
      bg: 'bg-amber-950/70 border-amber-500/40 text-amber-400',
      icon: AlertTriangle,
      label: 'MEDIUM RISK',
    },
    HIGH: {
      bg: 'bg-rose-950/70 border-rose-500/40 text-rose-400',
      icon: ShieldAlert,
      label: 'HIGH RISK',
    },
  }[norm] || {
    bg: 'bg-slate-800 border-slate-700 text-slate-300',
    icon: AlertTriangle,
    label: norm,
  }

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs font-semibold px-2.5 py-1 gap-1.5',
    lg: 'text-sm font-bold px-3 py-1.5 gap-2',
  }[size]

  const Icon = config.icon

  return (
    <span
      className={`inline-flex items-center rounded-md border tracking-wider uppercase ${config.bg} ${sizeClasses}`}
    >
      {showIcon && <Icon className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />}
      {config.label}
    </span>
  )
}
