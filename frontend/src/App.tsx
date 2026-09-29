import { useEffect, useState, useCallback } from 'react'
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Layers,
  Search,
  RefreshCw,
  AlertCircle,
  Activity,
  History,
} from 'lucide-react'
import { api, ApiError } from './services/api'
import type {
  HealthResponse,
  TransactionDetailResponse,
  TransactionScoreRequest,
  TransactionScoreResponse,
} from './types'
import { Header } from './components/Header'
import { StatCard } from './components/StatCard'
import { TransactionForm } from './components/TransactionForm'
import { RiskScoreCard } from './components/RiskScoreCard'
import { TransactionTable } from './components/TransactionTable'
import { TransactionDetails } from './components/TransactionDetails'
import { RiskDistributionChart } from './components/RiskDistributionChart'
import { RiskTimelineChart } from './components/RiskTimelineChart'

export function App() {
  // Navigation tab state
  const [activeTab, setActiveTab] = useState<'scoring' | 'history'>('scoring')

  // Connection & Health status state
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [isHealthLoading, setIsHealthLoading] = useState<boolean>(true)
  const [isHealthError, setIsHealthError] = useState<boolean>(false)

  // Current active user for history & context
  const [currentUserId, setCurrentUserId] = useState<string>('C123')
  const [searchInputUser, setSearchInputUser] = useState<string>('C123')

  // Scoring flow state
  const [isScoring, setIsScoring] = useState<boolean>(false)
  const [lastScoredResult, setLastScoredResult] = useState<TransactionScoreResponse | null>(null)
  const [scoringError, setScoringError] = useState<string | null>(null)

  // Transaction history state
  const [historyTransactions, setHistoryTransactions] = useState<TransactionDetailResponse[]>([])
  const [isHistoryLoading, setIsHistoryLoading] = useState<boolean>(false)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [totalUserTxns, setTotalUserTxns] = useState<number>(0)

  // Detailed transaction modal inspection state
  const [selectedTxnDetail, setSelectedTxnDetail] = useState<TransactionDetailResponse | null>(null)
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState<boolean>(false)

  // 1. Fetch Health Status
  const fetchHealth = useCallback(async () => {
    setIsHealthLoading(true)
    try {
      const data = await api.checkHealth()
      setHealth(data)
      setIsHealthError(false)
    } catch {
      setIsHealthError(true)
      setHealth(null)
    } finally {
      setIsHealthLoading(false)
    }
  }, [])

  // Poll health on mount & every 30s
  useEffect(() => {
    fetchHealth()
    const timer = setInterval(fetchHealth, 30000)
    return () => clearInterval(timer)
  }, [fetchHealth])

  // 2. Fetch User History
  const fetchUserHistory = useCallback(async (userIdToFetch: string) => {
    if (!userIdToFetch.trim()) return

    setIsHistoryLoading(true)
    setHistoryError(null)

    try {
      const res = await api.getUserTransactions(userIdToFetch.trim(), 50, 0)
      setHistoryTransactions(res.transactions)
      setTotalUserTxns(res.total_transactions)
      setCurrentUserId(userIdToFetch.trim())
    } catch (err) {
      if (err instanceof ApiError) {
        setHistoryError(err.message)
      } else {
        setHistoryError('Failed to load transaction history for this user.')
      }
      setHistoryTransactions([])
      setTotalUserTxns(0)
    } finally {
      setIsHistoryLoading(false)
    }
  }, [])

  // Load history for initial user on mount
  useEffect(() => {
    fetchUserHistory('C123')
  }, [fetchUserHistory])

  // 3. Handle Score Transaction
  const handleScoreTransaction = async (payload: TransactionScoreRequest) => {
    setIsScoring(true)
    setScoringError(null)

    try {
      const result = await api.scoreTransaction(payload)
      setLastScoredResult(result)

      // Automatically refresh history for this user so the table and stats stay updated
      if (payload.user_id) {
        setSearchInputUser(payload.user_id)
        await fetchUserHistory(payload.user_id)
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.details && err.details.length > 0) {
          const detailMsg = err.details.map((d) => `${d.field}: ${d.message}`).join(', ')
          setScoringError(`${err.message} (${detailMsg})`)
        } else {
          setScoringError(err.message)
        }
      } else {
        setScoringError('An unexpected error occurred while communicating with the scoring engine.')
      }
    } finally {
      setIsScoring(false)
    }
  }

  // 4. Open Transaction Detail
  const handleSelectTransaction = async (transactionId: string) => {
    setIsDetailModalOpen(true)
    setIsDetailLoading(true)

    try {
      const detail = await api.getTransaction(transactionId)
      setSelectedTxnDetail(detail)
    } catch (err) {
      if (err instanceof ApiError) {
        alert(`Error: ${err.message}`)
      } else {
        alert('Could not retrieve transaction details.')
      }
      setIsDetailModalOpen(false)
    } finally {
      setIsDetailLoading(false)
    }
  }

  // Compute summary stats from loaded transaction history
  const highRiskCount = historyTransactions.filter(
    (t) => String(t.risk_level).toUpperCase() === 'HIGH'
  ).length
  const mediumRiskCount = historyTransactions.filter(
    (t) => String(t.risk_level).toUpperCase() === 'MEDIUM'
  ).length
  const lowRiskCount = historyTransactions.filter(
    (t) => String(t.risk_level).toUpperCase() === 'LOW'
  ).length

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Global Header */}
      <Header
        health={health}
        isHealthLoading={isHealthLoading}
        isHealthError={isHealthError}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onRefreshHealth={fetchHealth}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Backend Warning Banner if Offline */}
        {isHealthError && (
          <div className="p-4 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-200 flex items-center justify-between gap-3 shadow-lg">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
              <div>
                <p className="text-sm font-semibold">Backend Service Offline</p>
                <p className="text-xs text-rose-300/80">
                  Ensure the FastAPI backend is running on <code className="font-mono text-white">http://127.0.0.1:8000</code>.
                </p>
              </div>
            </div>
            <button
              onClick={fetchHealth}
              className="text-xs px-3 py-1.5 rounded-lg bg-rose-900 hover:bg-rose-800 text-white font-medium transition"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Executive Summary Area */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <span>Telemetry Summary (User: <span className="text-white font-mono">{currentUserId}</span>)</span>
            </h2>
            <span className="text-xs text-slate-500 font-mono">
              Database Audit Records: {totalUserTxns}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard
              label="Audited Transactions"
              value={historyTransactions.length}
              sublabel={`Total recorded: ${totalUserTxns}`}
              icon={Activity}
              colorScheme="cyan"
            />
            <StatCard
              label="High-Risk Signals"
              value={highRiskCount}
              sublabel="Requires active verification"
              icon={ShieldAlert}
              colorScheme="rose"
            />
            <StatCard
              label="Medium-Risk"
              value={mediumRiskCount}
              sublabel="Stepped-up validation"
              icon={AlertTriangle}
              colorScheme="amber"
            />
            <StatCard
              label="Low-Risk (Safe)"
              value={lowRiskCount}
              sublabel="Normal behavioral baseline"
              icon={ShieldCheck}
              colorScheme="emerald"
            />
          </div>
        </section>

        {/* TAB 1: Scoring Studio */}
        {activeTab === 'scoring' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: Form */}
              <div className="lg:col-span-6 space-y-6">
                <TransactionForm
                  onSubmit={handleScoreTransaction}
                  isLoading={isScoring}
                />

                {scoringError && (
                  <div className="p-4 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-200 text-sm flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-white">Evaluation Error</p>
                      <p className="text-xs text-rose-300 mt-0.5 leading-relaxed">{scoringError}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column: Scoring Result Panel */}
              <div className="lg:col-span-6 space-y-6">
                {lastScoredResult ? (
                  <RiskScoreCard
                    result={lastScoredResult}
                    onViewHistory={() => {
                      if (lastScoredResult.user_id) {
                        setSearchInputUser(lastScoredResult.user_id)
                        fetchUserHistory(lastScoredResult.user_id)
                      }
                      setActiveTab('history')
                    }}
                  />
                ) : (
                  <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 p-12 text-center text-slate-500">
                    <ShieldAlert className="w-12 h-12 text-slate-700 mx-auto mb-3" />
                    <h3 className="text-base font-semibold text-slate-300">
                      No Real-Time Evaluation Result
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                      Submit a transaction on the left or select a preset to trigger ML model
                      scoring, behavioral rule evaluation, and PostgreSQL persistence.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Audit Snapshot below scoring studio */}
            {historyTransactions.length > 0 && (
              <div className="pt-4 border-t border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                    <History className="w-4 h-4 text-cyan-400" />
                    Recent Activity for <span className="font-mono text-cyan-300">{currentUserId}</span>
                  </h3>
                  <button
                    onClick={() => setActiveTab('history')}
                    className="text-xs text-cyan-400 hover:text-cyan-300 font-medium"
                  >
                    View Full Audit & Charts →
                  </button>
                </div>
                <TransactionTable
                  transactions={historyTransactions.slice(0, 5)}
                  isLoading={isHistoryLoading}
                  onSelectTransaction={handleSelectTransaction}
                />
              </div>
            )}
          </div>
        )}

        {/* TAB 2: Audit History & Intelligence Charts */}
        {activeTab === 'history' && (
          <div className="space-y-6">
            {/* User Search Bar */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3 w-full sm:w-auto">
                <div className="p-2 rounded-lg bg-slate-800 text-slate-400">
                  <Search className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Query User Audit Ledger</h3>
                  <p className="text-xs text-slate-400">Inspect historical transaction behavior and anomalies</p>
                </div>
              </div>

              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  fetchUserHistory(searchInputUser)
                }}
                className="flex items-center gap-2 w-full sm:w-auto"
              >
                <input
                  type="text"
                  value={searchInputUser}
                  onChange={(e) => setSearchInputUser(e.target.value)}
                  placeholder="Enter User ID (e.g. C123)"
                  className="px-3.5 py-2 rounded-lg bg-slate-950 border border-slate-800 text-sm text-white placeholder-slate-600 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition font-mono"
                />
                <button
                  type="submit"
                  disabled={isHistoryLoading}
                  className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs flex items-center gap-1.5 transition disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isHistoryLoading ? 'animate-spin' : ''}`} />
                  Query
                </button>
              </form>
            </div>

            {historyError && (
              <div className="p-4 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-200 text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{historyError}</span>
              </div>
            )}

            {/* Visual Analytics Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <RiskDistributionChart transactions={historyTransactions} />
              <RiskTimelineChart transactions={historyTransactions} />
            </div>

            {/* Complete Transaction Table */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-300">
                  Audit Records for <span className="font-mono text-cyan-300">{currentUserId}</span> ({historyTransactions.length})
                </h3>
                <span className="text-xs text-slate-500">
                  Click any transaction row to inspect complete risk explanation & telemetry
                </span>
              </div>

              <TransactionTable
                transactions={historyTransactions}
                isLoading={isHistoryLoading}
                onSelectTransaction={handleSelectTransaction}
              />
            </div>
          </div>
        )}
      </main>

      {/* Transaction Details Modal */}
      <TransactionDetails
        transaction={selectedTxnDetail}
        isOpen={isDetailModalOpen}
        isLoading={isDetailLoading}
        onClose={() => setIsDetailModalOpen(false)}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-600">
        FRAUDSCOPE AI • Real-Time Financial Fraud Intelligence Platform • Phase 4 Full-Stack Frontend
      </footer>
    </div>
  )
}

export default App
