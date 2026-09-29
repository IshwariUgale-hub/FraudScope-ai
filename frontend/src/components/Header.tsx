import React from 'react'
import { ShieldAlert, Zap, History } from 'lucide-react'
import type { HealthResponse } from '../types'
import { ConnectionStatus } from './ConnectionStatus'

interface HeaderProps {
  health: HealthResponse | null
  isHealthLoading: boolean
  isHealthError: boolean
  activeTab: 'scoring' | 'history'
  setActiveTab: (tab: 'scoring' | 'history') => void
  onRefreshHealth: () => void
}

export const Header: React.FC<HeaderProps> = ({
  health,
  isHealthLoading,
  isHealthError,
  activeTab,
  setActiveTab,
  onRefreshHealth,
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          {/* Brand Identity */}
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 text-cyan-400 shadow-lg shadow-cyan-500/10">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-black tracking-tight text-white m-0 p-0 font-sans">
                  FRAUDSCOPE <span className="text-cyan-400">AI</span>
                </h1>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-cyan-950 text-cyan-400 border border-cyan-800">
                  v1.0 REST
                </span>
              </div>
              <p className="text-xs text-slate-400 tracking-wide font-normal">
                Real-Time Financial Fraud Intelligence & Risk Scoring Platform
              </p>
            </div>
          </div>

          {/* Navigation & Connection Health */}
          <div className="flex items-center gap-3">
            {/* Nav tabs */}
            <div className="flex items-center p-1 rounded-xl bg-slate-900 border border-slate-800 text-xs">
              <button
                type="button"
                onClick={() => setActiveTab('scoring')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                  activeTab === 'scoring'
                    ? 'bg-cyan-500 text-slate-950 font-semibold shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Zap className="w-3.5 h-3.5" />
                Scoring Studio
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('history')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition ${
                  activeTab === 'history'
                    ? 'bg-cyan-500 text-slate-950 font-semibold shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <History className="w-3.5 h-3.5" />
                Audit History
              </button>
            </div>

            {/* Health pill */}
            <ConnectionStatus
              health={health}
              isLoading={isHealthLoading}
              isError={isHealthError}
              onRefresh={onRefreshHealth}
            />
          </div>
        </div>
      </div>
    </header>
  )
}
