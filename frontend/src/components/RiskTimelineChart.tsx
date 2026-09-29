import React from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import type { TransactionDetailResponse } from '../types'

interface RiskTimelineChartProps {
  transactions: TransactionDetailResponse[]
}

export const RiskTimelineChart: React.FC<RiskTimelineChartProps> = ({
  transactions,
}) => {
  // Sort transactions chronologically ascending for the timeline
  const sorted = [...transactions].sort((a, b) => a.timestamp - b.timestamp)

  const data = sorted.map((t) => {
    const timeLabel = new Date(t.timestamp * 1000).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    })

    return {
      transaction_id: t.transaction_id,
      time: timeLabel,
      score: t.risk_score,
      amount: t.amount,
      level: t.risk_level,
    }
  })

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-lg backdrop-blur">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Chronological Risk Trend
          </h4>
          <p className="text-[11px] text-slate-500">
            Temporal fluctuation of composite risk score across transactions
          </p>
        </div>
      </div>

      {data.length === 0 ? (
        <div className="h-44 flex items-center justify-center text-xs text-slate-500">
          No historical telemetry to plot
        </div>
      ) : (
        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.6} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="time"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#334155' }}
              />
              <YAxis
                domain={[0, 100]}
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#334155' }}
              />
              {/* High risk threshold indicator at score 70 */}
              <ReferenceLine y={70} stroke="#f43f5e" strokeDasharray="3 3" />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const item = payload[0].payload
                    return (
                      <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 shadow-xl text-xs space-y-1">
                        <div className="font-mono text-cyan-300 font-bold">{item.transaction_id}</div>
                        <div className="text-slate-400">Time: {item.time}</div>
                        <div className="text-slate-300 font-semibold">
                          Score: <span className="text-cyan-400">{item.score}/100</span> ({item.level})
                        </div>
                        <div className="text-slate-400">Amount: Rs {item.amount.toLocaleString()}</div>
                      </div>
                    )
                  }
                  return null
                }}
              />
              <Area
                type="monotone"
                dataKey="score"
                stroke="#06b6d4"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#scoreGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
