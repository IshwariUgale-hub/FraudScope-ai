import React from 'react'
import {
  X,
  Clock,
  MapPin,
  Smartphone,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Activity,
  History,
  Code,
} from 'lucide-react'
import type { TransactionDetailResponse } from '../types'
import { RiskBadge } from './RiskBadge'
import { ReasonList } from './ReasonList'

interface TransactionDetailsProps {
  transaction: TransactionDetailResponse | null
  isOpen: boolean
  isLoading: boolean
  onClose: () => void
}

export const TransactionDetails: React.FC<TransactionDetailsProps> = ({
  transaction,
  isOpen,
  isLoading,
  onClose,
}) => {
  const [showRawFeatures, setShowRawFeatures] = React.useState<boolean>(false)

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 text-slate-100">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition"
        >
          <X className="w-4 h-4" />
        </button>

        {isLoading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3">
            <Activity className="w-8 h-8 text-cyan-400 animate-spin" />
            <p className="text-sm text-slate-400">Loading transaction intelligence...</p>
          </div>
        ) : !transaction ? (
          <div className="py-12 text-center text-slate-400">
            Transaction details could not be retrieved.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header info */}
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase tracking-wider text-slate-500 font-mono">
                  Audit Record
                </span>
                <span className="text-slate-700">•</span>
                <span className="text-xs text-slate-400 font-mono">
                  ID: #{transaction.id}
                </span>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-3 mt-1.5">
                <h2 className="text-xl font-bold font-mono text-white">
                  {transaction.transaction_id}
                </h2>
                <RiskBadge level={transaction.risk_level} size="lg" />
              </div>
            </div>

            {/* Score & Probability Highlights */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                <span className="text-[11px] text-slate-400 uppercase font-mono">
                  Risk Score
                </span>
                <div className="text-2xl font-black font-mono mt-1 text-white">
                  {transaction.risk_score}
                  <span className="text-xs font-normal text-slate-500">/100</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                <span className="text-[11px] text-slate-400 uppercase font-mono">
                  ML Probability
                </span>
                <div className="text-2xl font-black font-mono mt-1 text-cyan-300">
                  {(transaction.ml_probability * 100).toFixed(1)}%
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                <span className="text-[11px] text-slate-400 uppercase font-mono">
                  ML Points
                </span>
                <div className="text-xl font-bold font-mono mt-1 text-indigo-300">
                  {transaction.ml_points.toFixed(1)}
                  <span className="text-xs font-normal text-slate-500">/60</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                <span className="text-[11px] text-slate-400 uppercase font-mono">
                  Rule Points
                </span>
                <div className="text-xl font-bold font-mono mt-1 text-amber-300">
                  {transaction.rule_points.toFixed(1)}
                  <span className="text-xs font-normal text-slate-500">/40</span>
                </div>
              </div>
            </div>

            {/* Recommended Action */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-start gap-3">
              {transaction.risk_level === 'HIGH' ? (
                <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              ) : transaction.risk_level === 'MEDIUM' ? (
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              ) : (
                <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              )}
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Recommended Action
                </span>
                <p className="text-sm font-semibold text-slate-100 mt-0.5">
                  {transaction.recommended_action}
                </p>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                  {transaction.summary}
                </p>
              </div>
            </div>

            {/* Telemetry & Backend-Derived Context */}
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Telemetry & Backend-Derived Behavioral Features
              </h4>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 flex items-center gap-1">
                    <History className="w-3.5 h-3.5" /> User / Card:
                  </span>
                  <span className="font-mono font-semibold text-slate-200 mt-0.5 block">
                    {transaction.user_id}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500">Amount:</span>
                  <span className="font-mono font-semibold text-slate-200 mt-0.5 block">
                    {transaction.currency} {transaction.amount.toLocaleString()}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" /> Time:
                  </span>
                  <span className="font-mono text-slate-300 mt-0.5 block">
                    {new Date(transaction.timestamp * 1000).toLocaleString()}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 flex items-center gap-1">
                    <Smartphone className="w-3.5 h-3.5" /> Device:
                  </span>
                  <span className="font-mono text-slate-300 mt-0.5 block truncate">
                    {transaction.device_id}{' '}
                    {transaction.is_new_device === 1 && (
                      <span className="text-amber-400 font-sans text-[10px] font-bold">
                        (NEW)
                      </span>
                    )}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500 flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" /> Location:
                  </span>
                  <span className="text-slate-300 mt-0.5 block">
                    {transaction.location}{' '}
                    {transaction.is_new_location === 1 && (
                      <span className="text-amber-400 font-sans text-[10px] font-bold">
                        (NEW)
                      </span>
                    )}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500">10m Velocity:</span>
                  <span className="font-mono text-cyan-300 font-bold mt-0.5 block">
                    {transaction.txn_count_10min} txns
                  </span>
                </div>

                <div>
                  <span className="text-slate-500">Time Since Prev:</span>
                  <span className="font-mono text-cyan-300 font-bold mt-0.5 block">
                    {transaction.seconds_since_prev < 60
                      ? `${transaction.seconds_since_prev.toFixed(0)}s`
                      : `${(transaction.seconds_since_prev / 60).toFixed(1)}m`}
                  </span>
                </div>

                <div>
                  <span className="text-slate-500">1h Velocity:</span>
                  <span className="font-mono text-slate-300 mt-0.5 block">
                    {transaction.txn_count_1h ?? 'N/A'} txns
                  </span>
                </div>
              </div>
            </div>

            {/* Reasons List */}
            <ReasonList reasons={transaction.reasons} />

            {/* Raw Features Inspector */}
            {transaction.features && (
              <div className="pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRawFeatures(!showRawFeatures)}
                  className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1.5 py-1"
                >
                  <Code className="w-3.5 h-3.5" />
                  <span>{showRawFeatures ? 'Hide' : 'Inspect'} Raw ML Feature Vector</span>
                </button>

                {showRawFeatures && (
                  <pre className="mt-2 p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-cyan-200 overflow-x-auto max-h-48">
                    {JSON.stringify(transaction.features, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
