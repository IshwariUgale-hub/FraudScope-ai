import React from 'react'
import { Eye, Clock, ShieldAlert } from 'lucide-react'
import type { TransactionDetailResponse } from '../types'
import { RiskBadge } from './RiskBadge'

interface TransactionTableProps {
  transactions: TransactionDetailResponse[]
  isLoading: boolean
  onSelectTransaction: (transactionId: string) => void
}

export const TransactionTable: React.FC<TransactionTableProps> = ({
  transactions,
  isLoading,
  onSelectTransaction,
}) => {
  if (isLoading) {
    return (
      <div className="py-16 text-center text-slate-400 bg-slate-900/40 rounded-xl border border-slate-800">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mb-3" />
        <p className="text-sm">Fetching recorded transaction telemetry...</p>
      </div>
    )
  }

  if (transactions.length === 0) {
    return (
      <div className="py-16 text-center text-slate-400 bg-slate-900/40 rounded-xl border border-slate-800">
        <ShieldAlert className="w-8 h-8 text-slate-600 mx-auto mb-2" />
        <p className="text-sm font-medium text-slate-300">No transactions recorded for this user.</p>
        <p className="text-xs text-slate-500 mt-1">
          Submit transactions above to build audit history and trigger real-time behavioral velocity tracking.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 shadow-lg">
      <table className="w-full text-left text-sm text-slate-300">
        <thead className="bg-slate-950/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
          <tr>
            <th className="py-3 px-4 font-mono">Transaction ID</th>
            <th className="py-3 px-4">Timestamp</th>
            <th className="py-3 px-4 text-right">Amount</th>
            <th className="py-3 px-4">Location</th>
            <th className="py-3 px-4">Device</th>
            <th className="py-3 px-4 text-center">Score</th>
            <th className="py-3 px-4">Risk Level</th>
            <th className="py-3 px-4">Recommended Action</th>
            <th className="py-3 px-4 text-center">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/80">
          {transactions.map((t) => {
            const dateStr = new Date(t.timestamp * 1000).toLocaleString(undefined, {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })

            return (
              <tr
                key={t.transaction_id}
                onClick={() => onSelectTransaction(t.transaction_id)}
                className="hover:bg-slate-800/40 cursor-pointer transition-colors group"
              >
                {/* Transaction ID */}
                <td className="py-3 px-4 font-mono font-semibold text-cyan-300 group-hover:text-cyan-200">
                  {t.transaction_id}
                </td>

                {/* Timestamp */}
                <td className="py-3 px-4 text-xs text-slate-400 whitespace-nowrap">
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-500" />
                    {dateStr}
                  </span>
                </td>

                {/* Amount */}
                <td className="py-3 px-4 text-right font-mono font-semibold text-white whitespace-nowrap">
                  {t.currency} {t.amount.toLocaleString()}
                </td>

                {/* Location */}
                <td className="py-3 px-4 text-xs text-slate-300 whitespace-nowrap">
                  {t.location}
                  {t.is_new_location === 1 && (
                    <span className="ml-1 text-[10px] text-amber-400 font-bold">(NEW)</span>
                  )}
                </td>

                {/* Device */}
                <td className="py-3 px-4 text-xs font-mono text-slate-400 max-w-[120px] truncate" title={t.device_id}>
                  {t.device_id}
                  {t.is_new_device === 1 && (
                    <span className="ml-1 text-[10px] text-amber-400 font-bold">(NEW)</span>
                  )}
                </td>

                {/* Risk Score */}
                <td className="py-3 px-4 text-center font-mono font-bold text-sm">
                  <span
                    className={
                      t.risk_score >= 70
                        ? 'text-rose-400'
                        : t.risk_score >= 40
                        ? 'text-amber-400'
                        : 'text-emerald-400'
                    }
                  >
                    {t.risk_score}
                  </span>
                </td>

                {/* Risk Level Badge */}
                <td className="py-3 px-4 whitespace-nowrap">
                  <RiskBadge level={t.risk_level} size="sm" />
                </td>

                {/* Recommended Action */}
                <td className="py-3 px-4 text-xs text-slate-300 max-w-[200px] truncate" title={t.recommended_action}>
                  {t.recommended_action}
                </td>

                {/* View Details Button */}
                <td className="py-3 px-4 text-center">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onSelectTransaction(t.transaction_id)
                    }}
                    className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-cyan-300 hover:bg-slate-700 transition"
                    title="View risk explanation details"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
