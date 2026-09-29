import React from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { TransactionDetailResponse } from '../types'

interface RiskDistributionChartProps {
  transactions: TransactionDetailResponse[]
}

export const RiskDistributionChart: React.FC<RiskDistributionChartProps> = ({
  transactions,
}) => {
  const counts = {
    LOW: 0,
    MEDIUM: 0,
    HIGH: 0,
  }

  transactions.forEach((t) => {
    const level = String(t.risk_level).toUpperCase()
    if (level === 'HIGH') counts.HIGH += 1
    else if (level === 'MEDIUM') counts.MEDIUM += 1
    else counts.LOW += 1
  })

  const data = [
    { name: 'Low Risk', level: 'LOW', count: counts.LOW, color: '#10b981' },
    { name: 'Medium Risk', level: 'MEDIUM', count: counts.MEDIUM, color: '#f59e0b' },
    { name: 'High Risk', level: 'HIGH', count: counts.HIGH, color: '#f43f5e' },
  ]

  const total = transactions.length

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-lg backdrop-blur">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Risk Tier Distribution
          </h4>
          <p className="text-[11px] text-slate-500">
            {total} evaluated transactions in current sample
          </p>
        </div>
      </div>

      {total === 0 ? (
        <div className="h-44 flex items-center justify-center text-xs text-slate-500">
          No transactions to plot
        </div>
      ) : (
        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <XAxis
                dataKey="name"
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#334155' }}
              />
              <YAxis
                allowDecimals={false}
                stroke="#64748b"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#334155' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.5rem',
                  fontSize: '12px',
                  color: '#f8fafc',
                }}
                cursor={{ fill: 'rgba(255, 255, 255, 0.04)' }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
