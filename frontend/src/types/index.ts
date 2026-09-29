/**
 * FraudScope AI TypeScript Type Definitions
 * Exact mapping of backend FastAPI Pydantic schemas (backend/app/schemas/transaction.py)
 */

export interface ReasonItem {
  signal: string
  detail: string
  points: number
}

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'

export interface TransactionScoreRequest {
  user_id?: string
  amount: number
  hour: number
  device_id: string
  location: string
  timestamp?: number
  txn_count_10min?: number
  seconds_since_prev?: number
  transaction_id?: string
  is_new_device?: number
  is_new_location?: number
  txn_count_1h?: number
  currency?: string
}

export interface TransactionScoreResponse {
  transaction_id: string
  risk_score: number
  risk_level: RiskLevel | string
  ml_probability: number
  ml_points: number
  rule_points: number
  reasons: ReasonItem[]
  summary: string
  recommended_action: string
  user_id?: string | null
  features?: Record<string, unknown> | null
}

export interface TransactionDetailResponse {
  id: number
  transaction_id: string
  user_id: string
  amount: number
  timestamp: number
  device_id: string
  location: string
  currency: string
  txn_count_10min: number
  txn_count_1h?: number | null
  seconds_since_prev: number
  is_new_device?: number | null
  is_new_location?: number | null
  risk_score: number
  risk_level: RiskLevel | string
  ml_probability: number
  ml_points: number
  rule_points: number
  recommended_action: string
  summary: string
  reasons: ReasonItem[]
  features?: Record<string, unknown> | null
  created_at?: string | null
}

export interface UserTransactionsResponse {
  user_id: string
  total_transactions: number
  transactions: TransactionDetailResponse[]
}

export interface HealthResponse {
  status: 'ok' | 'degraded' | string
  database: 'connected' | 'disconnected' | string
}

export interface ApiValidationErrorDetail {
  field: string
  message: string
  type: string
}

export interface ApiErrorResponse {
  error: string
  message: string
  details?: ApiValidationErrorDetail[]
}
