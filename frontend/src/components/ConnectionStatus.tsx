import React from 'react'
import { Activity, AlertTriangle, CheckCircle2 } from 'lucide-react'
import type { HealthResponse } from '../types'

interface ConnectionStatusProps {
  health: HealthResponse | null
  isLoading: boolean
  isError: boolean
  onRefresh?: () => void
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  health,
  isLoading,
  isError,
  onRefresh,
}) => {
  const isBackendOk = !isError && health !== null && (health.status === 'ok' || health.status === 'degraded')
  const isDbOk = !isError && health !== null && health.database === 'connected'

  return (
    <div
      onClick={onRefresh}
      title="Click to re-check backend health"
      className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-slate-900/90 border border-slate-800 text-xs shadow-inner cursor-pointer hover:border-slate-700 transition-colors"
    >
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2 w-2">
          {isBackendOk ? (
            <>
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </>
          ) : (
            <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500" />
          )}
        </span>
        <span className="text-slate-400">Backend:</span>
        <span className={isBackendOk ? 'text-emerald-400 font-medium' : 'text-rose-400 font-medium'}>
          {isLoading ? 'Checking...' : isBackendOk ? 'Connected' : 'Offline'}
        </span>
      </div>

      <span className="text-slate-700">|</span>

      <div className="flex items-center gap-1.5">
        {isDbOk ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        ) : (
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
        )}
        <span className="text-slate-400">Database:</span>
        <span className={isDbOk ? 'text-emerald-400 font-medium' : 'text-amber-400 font-medium'}>
          {isDbOk ? 'Connected' : isBackendOk ? 'Disconnected' : 'Offline'}
        </span>
      </div>

      {isLoading && <Activity className="w-3 h-3 text-cyan-400 animate-spin ml-1" />}
    </div>
  )
}
