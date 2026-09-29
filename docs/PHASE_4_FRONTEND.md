# Phase 4: FraudScope AI Full-Stack React Frontend

This document details the architecture, setup, API integrations, and features implemented during **Phase 4** of the FraudScope AI migration.

---

## 1. Overview & Architecture

Phase 4 introduces a modern, high-performance React frontend built with **Vite**, **TypeScript**, **Tailwind CSS**, and **Recharts**. The frontend acts as the primary full-stack user interface for real-time transaction scoring, behavioral explainability, and customer audit telemetry.

### System Architecture Flow:

```text
React Frontend (Vite + TypeScript + Tailwind)
      ↓  (HTTP REST / JSON via typed api.ts)
FastAPI REST API (Port 8000)
      ↓  (SQLAlchemy ORM)
PostgreSQL / SQLite Storage (transactions table)
      ↓  (Automated Behavioral Context Derivation)
Existing FraudScope ML Engine (HistGradientBoosting + Rule Engine)
      ↓  (Composite Risk Score 0–100, Explanations, Actions)
React UI (Real-Time Cards, Recharts Analytics, Audit Ledger)
```

The Streamlit dashboard (`dashboard/app.py`) remains untouched as the original standalone prototype.

---

## 2. Directory & Component Structure

```text
frontend/
├── public/
│   ├── favicon.svg
├── src/
│   ├── components/
│   │   ├── ConnectionStatus.tsx       # Live Backend & DB connectivity pill with heartbeat
│   │   ├── Header.tsx                 # Top navigation, brand identity & health indicator
│   │   ├── ReasonList.tsx             # Itemized explainable intelligence signals & point weights
│   │   ├── RiskBadge.tsx              # Color-coded tier badges (LOW, MEDIUM, HIGH)
│   │   ├── RiskDistributionChart.tsx  # Recharts bar breakdown of risk tier distribution
│   │   ├── RiskScoreCard.tsx          # Composite dial (0-100), ML prob, actions, summary
│   │   ├── RiskTimelineChart.tsx      # Recharts temporal risk score fluctuation & thresholds
│   │   ├── StatCard.tsx               # Executive KPI cards (Audited txns, High-Risk counts)
│   │   ├── TransactionDetails.tsx     # Full telemetry inspection modal & raw vector JSON viewer
│   │   ├── TransactionForm.tsx        # Scoring input panel with quick anomaly & normal presets
│   │   └── TransactionTable.tsx       # Interactive audit ledger with row inspection links
│   ├── services/
│   │   └── api.ts                     # Centralized typed HTTP client with error formatting
│   ├── types/
│   │   └── index.ts                   # TypeScript interfaces strictly mapped to FastAPI schemas
│   ├── App.tsx                        # Master dashboard layout, state management, and tab routing
│   ├── index.css                      # Tailwind CSS v4 styling & dark theme tokens
│   └── main.tsx                       # React 19 application mount
├── .env                               # Local environment configuration
├── .env.example                       # Environment configuration template
├── package.json                       # Dependencies & build scripts
├── tsconfig.json                      # Root TypeScript configuration
├── tsconfig.app.json                  # Application TypeScript compiler settings
└── vite.config.ts                     # Vite configuration with Tailwind plugin & backend proxy
```

---

## 3. API Integration Layer

All backend communication is centralized in `frontend/src/services/api.ts` using strict TypeScript typings matching backend Pydantic models in `backend/app/schemas/transaction.py`:

| HTTP Method | Backend Endpoint | Function in `api.ts` | Purpose |
|-------------|------------------|----------------------|---------|
| `GET` | `/health` | `api.checkHealth()` | Validates FastAPI service and database connectivity |
| `POST` | `/api/v1/transactions/score` | `api.scoreTransaction(payload)` | Evaluates transaction telemetry, derives context, & persists record |
| `GET` | `/api/v1/transactions/{id}` | `api.getTransaction(id)` | Retrieves detailed transaction record, reasons, & feature vector |
| `GET` | `/api/v1/users/{user_id}/transactions` | `api.getUserTransactions(userId, limit, skip)` | Fetches paginated user transaction history & risk scores |

### Automated Behavioral Context (Zero-Manual-Entry)
The frontend deliberately **never** prompts the user for velocity metrics (`txn_count_10min`), time deltas (`seconds_since_prev`), or device novelty flags. These values are autonomously computed by the FastAPI service from historical transaction records in the database.

---

## 4. Local Setup & Execution Guide

### Prerequisites
- Node.js (v18+ recommended; tested with v22.23.0)
- Python (v3.10+; tested with Python 3.14.0)

### Step 1: Start the FastAPI Backend
From the repository root:
```bash
# Ensure dependencies are installed
pip install -r backend/requirements.txt

# Start FastAPI server on port 8000
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Verify backend health:
```bash
curl http://127.0.0.1:8000/health
# Returns: {"status":"ok","database":"connected"}
```

### Step 2: Start the React Frontend
In a new terminal window, navigate to `frontend/`:
```bash
cd frontend

# Install packages (if not already installed)
npm install

# Start Vite development server
npm run dev
```
The application will launch at `http://127.0.0.1:5173/` or `http://localhost:5173/`.

---

## 5. Environment Variables

### Frontend (`frontend/.env`):
```ini
# Base URL of the FastAPI backend service
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Backend (`backend/.env` or root `.env`):
```ini
# Optional database URL (defaults to SQLite fallback if PostgreSQL is not set)
DATABASE_URL=sqlite:///fraudscope.db

# Allowed CORS origins
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173
```

---

## 6. Available Dashboard Features

1. **Header & Health Heartbeat**:
   - Displays real-time connectivity status for FastAPI backend and PostgreSQL/SQLite database.
   - Auto-polls `/health` every 30 seconds with manual click-to-refresh.

2. **Executive Telemetry Summary**:
   - Real-time counters for Audited Transactions, High-Risk Signals, Medium-Risk flags, and Low-Risk transactions.

3. **Real-Time Scoring Studio**:
   - Dynamic input form for user ID, amount, device fingerprint, city, and hour of day.
   - Quick presets for **High-Risk Anomaly** and **Normal Routine** test scenarios.
   - Instant visual score card displaying:
     - Composite Risk Score dial (`0–100`)
     - Risk Tier Badge (`LOW`, `MEDIUM`, `HIGH`)
     - ML Probability percentage from `HistGradientBoostingClassifier`
     - Score weight breakdown: ML Model Points (`max 60`) vs. Rule Engine Points (`max 40`)
     - Prescribed operational action
     - Executive natural language explanation summary
     - Granular list of triggered signals with exact points contribution

4. **Audit History & Timeline**:
   - Query user transaction ledgers by customer ID.
   - Interactive Recharts **Risk Tier Distribution** bar visualization.
   - Chronological Recharts **Risk Trend Area Chart** tracking temporal score fluctuations with a danger threshold reference line at 70.
   - Full audit table with row-level view triggers.

5. **Deep Inspection Modal**:
   - Inspect complete telemetry, database audit metadata, backend-derived velocity (`txn_count_10min`, `txn_count_1h`), time delta (`seconds_since_prev`), novelty flags (`is_new_device`, `is_new_location`), and raw ML feature vectors.

6. **Safety & Security Tone**:
   - Clear and objective risk terminology ("High Risk", "Requires verification", "Potentially suspicious") rather than accusatory or definitive claims of fraud.

---

## 7. Known Limitations & Next Steps

- **Authentication**: Phase 4 focuses on core scoring and telemetry visualization; user session authentication and role-based access control (RBAC) are planned for future phases.
- **WebSocket Streaming**: Transaction updates are refreshed after score submission or manual ledger query; live streaming via WebSockets will be introduced in subsequent phases.
- **Cross-Browser Verification**: Verified via HTTP 200 checks, Vite production build validation, and end-to-end Python API integration suites; internal automated browser subagent driver download was unavailable due to upstream Azure CDN 404 for Windows Playwright package.
