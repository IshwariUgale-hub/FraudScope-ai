import React from 'react'
import {
  AlertTriangle,
  Cpu,
  Layers,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  TrendingUp,
} from 'lucide-react'
import type { TransactionScoreResponse } from '../types'
import { RiskBadge } from './RiskBadge'
import { ReasonList } from './ReasonList'

interface RiskScoreCardProps {
  result: TransactionScoreResponse
  onViewHistory?: () => void
}

export const RiskScoreCard: React.FC<RiskScoreCardProps> = ({
  result,
  onViewHistory,
}) => {
  const normLevel = String(result.risk_level).toUpperCase()

  const cardStyle = {
    LOW: {
      border: 'border-emerald-500/30',
      bgGlow: 'bg-emerald-500/5',
      scoreText: 'text-emerald-400',
      statusNotice: 'text-emerald-300 bg-emerald-950/40 border-emerald-500/30',
      icon: ShieldCheck,
      disclaimer: 'Transaction patterns align with standard legitimate customer behavior.',
    },
    MEDIUM: {
      border: 'border-amber-500/30',
      bgGlow: 'bg-amber-500/5',
      scoreText: 'text-amber-400',
      statusNotice: 'text-amber-300 bg-amber-950/40 border-amber-500/30',
      icon: AlertTriangle,
      disclaimer: 'Moderate behavioral deviation detected. Stepped-up verification recommended.',
    },
    HIGH: {
      border: 'border-rose-500/40',
      bgGlow: 'bg-rose-500/10',
      scoreText: 'text-rose-400',
      statusNotice: 'text-rose-300 bg-rose-950/50 border-rose-500/40',
      icon: ShieldAlert,
      disclaimer: 'High anomaly patterns detected. Requires active verification before clearing.',
    },
  }[normLevel] || {
    border: 'border-slate-700',
    bgGlow: 'bg-slate-900',
    scoreText: 'text-slate-200',
    statusNotice: 'text-slate-300 bg-slate-900 border-slate-700',
    icon: AlertTriangle,
    disclaimer: 'Assessment recorded.',
  }

  const StatusIcon = cardStyle.icon

  return (
    <div
      className={`rounded-2xl border ${cardStyle.border} ${cardStyle.bgGlow} bg-slate-900/80 p-6 shadow-2xl backdrop-blur transition-all duration-300`}
    >
      {/* Top Banner / Assessment Tag */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-5 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-slate-800/80 border border-slate-700">
            <StatusIcon className="w-5 h-5 text-slate-300" />
          </div>
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-widest font-mono">
              Assessment Result
            </div>
            <div className="text-sm font-semibold text-slate-200 font-mono">
              {result.transaction_id}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <RiskBadge level={result.risk_level} size="lg" />
          {result.user_id && onViewHistory && (
            <button
              onClick={onViewHistory}
              className="text-xs flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
              title="View full user history"
            >
              <span>User History</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Primary Score & Key Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 my-6 items-center">
        {/* Main Composite Score Dial */}
        <div className="md:col-span-5 flex flex-col items-center justify-center p-6 rounded-xl bg-slate-950/70 border border-slate-800/80">
          <span className="text-xs uppercase tracking-widest text-slate-400 font-mono">
            Composite Risk Score
          </span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className={`text-6xl font-black font-mono tracking-tighter ${cardStyle.scoreText}`}>
              {result.risk_score}
            </span>
            <span className="text-2xl font-bold text-slate-500 font-mono">/ 100</span>
          </div>

          <div className="w-full bg-slate-800 rounded-full h-2.5 mt-4 overflow-hidden border border-slate-700/50">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                normLevel === 'HIGH'
                  ? 'bg-rose-500'
                  : normLevel === 'MEDIUM'
                  ? 'bg-amber-500'
                  : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, result.risk_score))}%` }}
            />
          </div>

          <p className="text-xs text-slate-400 mt-3 text-center italic">
            {cardStyle.disclaimer}
          </p>
        </div>

        {/* Detailed Breakdown Grid */}
        <div className="md:col-span-7 grid grid-cols-2 gap-3.5">
          {/* ML Probability */}
          <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <TrendingUp className="w-4 h-4 text-cyan-400" />
              <span>ML Probability</span>
            </div>
            <div className="text-xl font-bold font-mono text-cyan-200 mt-1">
              {(result.ml_probability * 100).toFixed(1)}%
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">HistGradientBoosting</div>
          </div>

          {/* ML Points */}
          <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Cpu className="w-4 h-4 text-indigo-400" />
              <span>ML Model Points</span>
            </div>
            <div className="text-xl font-bold font-mono text-indigo-200 mt-1">
              {result.ml_points.toFixed(1)}{' '}
              <span className="text-xs text-slate-500 font-normal">/ 60</span>
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Statistical weight</div>
          </div>

          {/* Rule Points */}
          <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Layers className="w-4 h-4 text-amber-400" />
              <span>Rule Engine Points</span>
            </div>
            <div className="text-xl font-bold font-mono text-amber-200 mt-1">
              {result.rule_points.toFixed(1)}{' '}
              <span className="text-xs text-slate-500 font-normal">/ 40</span>
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Behavioral rules</div>
          </div>

          {/* Customer / Target User */}
          <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="font-mono text-slate-500">ID</span>
              <span>Account / User</span>
            </div>
            <div className="text-lg font-bold font-mono text-slate-200 mt-1 truncate">
              {result.user_id || 'Anonymous'}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Audited cardholder</div>
          </div>
        </div>
      </div>

      {/* Recommended Action Pill */}
      <div className={`p-4 rounded-xl border mb-5 ${cardStyle.statusNotice}`}>
        <div className="flex items-start gap-3">
          <StatusIcon className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <div className="text-xs font-bold uppercase tracking-wider">
              Recommended Action
            </div>
            <div className="text-sm font-semibold mt-0.5">
              {result.recommended_action}
            </div>
          </div>
        </div>
      </div>

      {/* Natural Language Executive Summary */}
      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 mb-6">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
          Executive Intelligence Summary
        </h4>
        <p className="text-sm text-slate-300 leading-relaxed">
          {result.summary}
        </p>
      </div>

      {/* Itemized Reasons */}
      <ReasonList reasons={result.reasons} />
    </div>
  )
}
