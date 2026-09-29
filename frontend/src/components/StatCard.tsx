import React from 'react'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: number | string
  sublabel?: string
  icon: LucideIcon
  colorScheme?: 'cyan' | 'emerald' | 'amber' | 'rose' | 'slate'
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  sublabel,
  icon: Icon,
  colorScheme = 'slate',
}) => {
  const styles = {
    cyan: {
      card: 'border-cyan-500/20 bg-slate-900/60 hover:border-cyan-500/40',
      iconBox: 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30',
      val: 'text-cyan-200',
    },
    emerald: {
      card: 'border-emerald-500/20 bg-slate-900/60 hover:border-emerald-500/40',
      iconBox: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30',
      val: 'text-emerald-400',
    },
    amber: {
      card: 'border-amber-500/20 bg-slate-900/60 hover:border-amber-500/40',
      iconBox: 'bg-amber-500/10 text-amber-400 border border-amber-500/30',
      val: 'text-amber-400',
    },
    rose: {
      card: 'border-rose-500/20 bg-slate-900/60 hover:border-rose-500/40',
      iconBox: 'bg-rose-500/10 text-rose-400 border border-rose-500/30',
      val: 'text-rose-400',
    },
    slate: {
      card: 'border-slate-800 bg-slate-900/60 hover:border-slate-700',
      iconBox: 'bg-slate-800 text-slate-300 border border-slate-700',
      val: 'text-white',
    },
  }[colorScheme]

  return (
    <div
      className={`rounded-xl border p-4.5 transition-all duration-200 flex items-start justify-between ${styles.card}`}
    >
      <div>
        <p className="text-xs font-medium text-slate-400 tracking-wide uppercase">{label}</p>
        <p className={`text-2xl font-bold mt-1 tracking-tight ${styles.val}`}>{value}</p>
        {sublabel && <p className="text-xs text-slate-500 mt-1">{sublabel}</p>}
      </div>
      <div className={`p-2.5 rounded-lg ${styles.iconBox}`}>
        <Icon className="w-5 h-5" />
      </div>
    </div>
  )
}
