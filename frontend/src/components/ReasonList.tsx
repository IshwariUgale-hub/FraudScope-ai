import React from 'react'
import { AlertCircle, AlertOctagon, Info } from 'lucide-react'
import type { ReasonItem } from '../types'

interface ReasonListProps {
  reasons: ReasonItem[]
}

export const ReasonList: React.FC<ReasonListProps> = ({ reasons }) => {
  if (!reasons || reasons.length === 0) {
    return (
      <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800 text-sm text-slate-400 flex items-center gap-2">
        <Info className="w-4 h-4 text-slate-500" />
        No behavioral anomaly or risk signals triggered for this transaction.
      </div>
    )
  }

  return (
    <div className="space-y-2.5">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
        <span>Why this score? (Explainable Intelligence)</span>
        <span className="text-slate-600">({reasons.length} signals flagged)</span>
      </h4>

      <div className="space-y-2">
        {reasons.map((item, index) => {
          const isHighWeight = item.points >= 20
          const isMediumWeight = item.points >= 10 && item.points < 20

          return (
            <div
              key={index}
              className={`p-3 rounded-lg border text-sm transition-all ${
                isHighWeight
                  ? 'bg-rose-950/20 border-rose-800/40 text-rose-200'
                  : isMediumWeight
                  ? 'bg-amber-950/20 border-amber-800/40 text-amber-200'
                  : 'bg-slate-900/80 border-slate-800 text-slate-200'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2.5">
                  {isHighWeight ? (
                    <AlertOctagon className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                  ) : isMediumWeight ? (
                    <AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                  ) : (
                    <Info className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
                  )}

                  <div>
                    <span className="font-semibold text-white tracking-wide">
                      {item.signal}
                    </span>
                    <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                      {item.detail}
                    </p>
                  </div>
                </div>

                <div className="shrink-0 text-right">
                  <span
                    className={`inline-block text-xs font-mono font-bold px-2 py-0.5 rounded ${
                      isHighWeight
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : isMediumWeight
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : 'bg-slate-800 text-slate-300 border border-slate-700'
                    }`}
                  >
                    +{item.points.toFixed(0)} pts
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
