/**
 * FraudScope AI Centralized API Service Layer
 * Interfaces with FastAPI backend endpoints.
 */

import type {
  HealthResponse,
  TransactionDetailResponse,
  TransactionScoreRequest,
  TransactionScoreResponse,
  UserTransactionsResponse,
} from '../types'

export class ApiError extends Error {
  statusCode?: number
  details?: Array<{ field: string; message: string; type: string }>

  constructor(
    message: string,
    statusCode?: number,
    details?: Array<{ field: string; message: string; type: string }>
  ) {
    super(message)
    this.name = 'ApiError'
    this.statusCode = statusCode
    this.details = details
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`

  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (options.body && typeof options.body === 'string') {
    headers['Content-Type'] = 'application/json'
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    })

    if (!res.ok) {
      let errorMessage = `Request failed with status ${res.status}`
      let details: Array<{ field: string; message: string; type: string }> | undefined

      try {
        const errorData = await res.json()
        if (errorData.message) {
          errorMessage = errorData.message
        } else if (errorData.error) {
          errorMessage = typeof errorData.error === 'string' ? errorData.error : JSON.stringify(errorData.error)
        } else if (errorData.detail) {
          errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail)
        }
        if (Array.isArray(errorData.details)) {
          details = errorData.details
        }
      } catch {
        // Fall back to status text
        errorMessage = res.statusText || errorMessage
      }

      throw new ApiError(errorMessage, res.status, details)
    }

    return (await res.json()) as T
  } catch (err) {
    if (err instanceof ApiError) {
      throw err
    }
    // Network or connection failure
    throw new ApiError(
      'Unable to connect to FraudScope backend. Please ensure FastAPI is running.',
      0
    )
  }
}

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, '') ||
  'http://127.0.0.1:8000'

export const api = {
  /**
   * Health check for FastAPI and database connectivity
   */
  async checkHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/health')
  },

  /**
   * Evaluates a transaction against ML and behavioral rule engines and persists to DB
   */
  async scoreTransaction(payload: TransactionScoreRequest): Promise<TransactionScoreResponse> {
    return request<TransactionScoreResponse>('/api/v1/transactions/score', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /**
   * Retrieves full transaction record and risk evaluation details by transaction ID
   */
  async getTransaction(transactionId: string): Promise<TransactionDetailResponse> {
    return request<TransactionDetailResponse>(
      `/api/v1/transactions/${encodeURIComponent(transactionId)}`
    )
  },

  /**
   * Retrieves recent transaction history and risk scores for a user
   */
  async getUserTransactions(
    userId: string,
    limit: number = 20,
    skip: number = 0
  ): Promise<UserTransactionsResponse> {
    const params = new URLSearchParams({
      limit: String(limit),
      skip: String(skip),
    })
    return request<UserTransactionsResponse>(
      `/api/v1/users/${encodeURIComponent(userId)}/transactions?${params.toString()}`
    )
  },
}
