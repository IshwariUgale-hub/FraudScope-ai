import React, { useState } from 'react'
import {
  Send,
  Zap,
  ShieldAlert,
  ShieldCheck,
  RotateCcw,
  Sparkles,
  Info,
} from 'lucide-react'
import type { TransactionScoreRequest } from '../types'

interface TransactionFormProps {
  onSubmit: (payload: TransactionScoreRequest) => Promise<void>
  isLoading: boolean
  onPresetSelect?: (presetName: string) => void
}

export const TransactionForm: React.FC<TransactionFormProps> = ({
  onSubmit,
  isLoading,
}) => {
  const currentHour = new Date().getHours()

  const [userId, setUserId] = useState<string>('C123')
  const [amount, setAmount] = useState<string>('85000')
  const [hour, setHour] = useState<number>(2)
  const [deviceId, setDeviceId] = useState<string>('device_new')
  const [location, setLocation] = useState<string>('Delhi')
  const [currency] = useState<string>('Rs')
  const [validationError, setValidationError] = useState<string | null>(null)

  const handleApplyPreset = (type: 'high-risk' | 'normal' | 'velocity') => {
    if (type === 'high-risk') {
      setUserId('C123')
      setAmount('85000')
      setHour(2)
      setDeviceId('device_new')
      setLocation('Delhi')
    } else if (type === 'normal') {
      setUserId('C123')
      setAmount('1500')
      setHour(14)
      setDeviceId('device_trusted_primary')
      setLocation('Mumbai')
    } else if (type === 'velocity') {
      setUserId('USER_VELOCITY_TEST')
      setAmount('42000')
      setHour(hour)
      setDeviceId('device_mobile_02')
      setLocation('Bengaluru')
    }
    setValidationError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setValidationError(null)

    const parsedAmount = parseFloat(amount)
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      setValidationError('Please enter a valid positive transaction amount.')
      return
    }

    if (!deviceId.trim()) {
      setValidationError('Device ID is required.')
      return
    }

    if (!location.trim()) {
      setValidationError('Location is required.')
      return
    }

    if (hour < 0 || hour > 23) {
      setValidationError('Hour must be between 0 and 23.')
      return
    }

    const payload: TransactionScoreRequest = {
      user_id: userId.trim() ? userId.trim() : undefined,
      amount: parsedAmount,
      hour: Number(hour),
      device_id: deviceId.trim(),
      location: location.trim(),
      currency,
    }

    await onSubmit(payload)
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800 mb-5">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            Evaluate Real-Time Transaction
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Submit transactional telemetry for ML scoring and behavioral analysis.
          </p>
        </div>

        {/* Quick Test Presets */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 hidden sm:inline">Presets:</span>
          <button
            type="button"
            onClick={() => handleApplyPreset('high-risk')}
            className="text-xs flex items-center gap-1 px-2.5 py-1 rounded bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-800/60 transition"
            title="High-risk anomaly test case"
          >
            <ShieldAlert className="w-3 h-3 text-rose-400" />
            High-Risk Anomaly
          </button>
          <button
            type="button"
            onClick={() => handleApplyPreset('normal')}
            className="text-xs flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-300 border border-emerald-800/60 transition"
            title="Legitimate low-risk test case"
          >
            <ShieldCheck className="w-3 h-3 text-emerald-400" />
            Normal Routine
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {validationError && (
          <div className="p-3 rounded-lg bg-rose-950/70 border border-rose-700 text-xs text-rose-200">
            {validationError}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* User ID */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Customer / User ID
            </label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g. C123"
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-sm text-slate-100 placeholder-slate-600 transition"
            />
            <span className="text-[11px] text-slate-500 mt-1 block">
              Used to look up historical baseline in database
            </span>
          </div>

          {/* Amount */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Transaction Amount ({currency})
            </label>
            <input
              type="number"
              step="any"
              min="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="85000"
              required
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-sm text-slate-100 font-mono placeholder-slate-600 transition"
            />
            <span className="text-[11px] text-slate-500 mt-1 block">
              Compared against peer and user spending norms
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Device ID */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Device Fingerprint
            </label>
            <input
              type="text"
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              placeholder="device_new"
              required
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-sm text-slate-100 font-mono placeholder-slate-600 transition"
            />
          </div>

          {/* Location */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Location / City
            </label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Delhi"
              required
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-sm text-slate-100 placeholder-slate-600 transition"
            />
          </div>

          {/* Hour */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Hour of Day (0–23)
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="23"
                value={hour}
                onChange={(e) => setHour(parseInt(e.target.value) || 0)}
                required
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 text-sm text-slate-100 font-mono transition"
              />
              <button
                type="button"
                onClick={() => setHour(currentHour)}
                className="shrink-0 text-xs px-2.5 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
                title="Use current local hour"
              >
                Now
              </button>
            </div>
          </div>
        </div>

        {/* Backend Derived Context Notice */}
        <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs text-slate-400 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <span className="font-semibold text-slate-300">Automated Context: </span>
            Velocity (<code className="text-cyan-300">txn_count_10min</code>), time delta (
            <code className="text-cyan-300">seconds_since_prev</code>), and device/location novelty are{' '}
            <span className="text-slate-200">autonomously derived by the backend</span> from PostgreSQL
            history. No manual entry needed.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={() => handleApplyPreset('normal')}
            className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800/50 hover:bg-slate-800 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset to Routine
          </button>

          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-sm shadow-lg shadow-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition"
          >
            {isLoading ? (
              <>
                <Sparkles className="w-4 h-4 animate-spin" />
                Scoring Engine Active...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Score & Persist Transaction
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
