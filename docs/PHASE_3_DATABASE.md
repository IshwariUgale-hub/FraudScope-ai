# FRAUDSCOPE AI — Phase 3 Database & Persistence Architecture

**Document Version:** 1.0.0  
**Phase:** 3 (PostgreSQL Persistence & Behavioral Context Migration)  
**Status:** Completed & Verified  

---

## 1. Overview & Objectives

In Phase 3 of the FRAUDSCOPE AI full-stack migration, we integrated a relational database persistence layer using **SQLAlchemy 2.x** and **PostgreSQL** (with zero-friction SQLite fallback for local test suites).

The primary architectural shift in this phase is moving the source of truth for **customer behavioural history** into the database:
- Prior to Phase 3, behavioral velocity (`txn_count_10min`) and time delta (`seconds_since_prev`) were passed as manual client input sliders in the Streamlit prototype.
- In Phase 3, the FastAPI backend automatically queries historical transactions stored in PostgreSQL for that customer, calculates real-time velocity windows (10-minute, 1-hour), determines elapsed seconds since the prior transaction, detects device and location novelty, and passes this derived context to the existing **FraudScope ML Engine** and **Risk Engine**.
- Every evaluated transaction, along with its composite risk score, risk level, rule penalties, reasons, and features, is persisted to PostgreSQL.

---

## 2. Database Architecture & Schema

### 2.1 Schema Definition (`transactions` Table)

The persistence model is implemented in `backend/app/models/transaction.py` using standard SQLAlchemy 2.0 `DeclarativeBase`:

| Column | Type | Constraints / Defaults | Description |
|---|---|---|---|
| `id` | `INTEGER` | Primary Key, Autoincrement | Internal synthetic record ID |
| `transaction_id` | `VARCHAR(64)` | Unique, Indexed, Not Null | Public transaction reference ID (e.g., `TXN-02A04F64`) |
| `user_id` | `VARCHAR(64)` | Indexed, Not Null | Customer or card identifier |
| `amount` | `FLOAT` | Not Null | Transaction monetary amount |
| `timestamp` | `BIGINT` | Indexed, Not Null | Chronological Unix epoch seconds |
| `device_id` | `VARCHAR(128)` | Not Null | Device fingerprint / channel proxy |
| `location` | `VARCHAR(128)` | Not Null | City or billing region |
| `currency` | `VARCHAR(16)` | Default `'Rs'`, Not Null | Transaction currency symbol |
| `txn_count_10min` | `INTEGER` | Default `1`, Not Null | Evaluated transactions in trailing 10-minute window |
| `txn_count_1h` | `INTEGER` | Nullable | Evaluated transactions in trailing 1-hour window |
| `seconds_since_prev` | `FLOAT` | Default `86400.0`, Not Null | Evaluated seconds elapsed since user's prior transaction |
| `is_new_device` | `INTEGER` | Default `0`, Nullable | 1 if device unseen in customer history, else 0 |
| `is_new_location` | `INTEGER` | Default `0`, Nullable | 1 if location unseen in customer history, else 0 |
| `risk_score` | `INTEGER` | Not Null | Composite risk score (0 to 100) |
| `risk_level` | `VARCHAR(16)` | Not Null | Risk tier (`LOW`, `MEDIUM`, `HIGH`) |
| `ml_probability` | `FLOAT` | Not Null | Raw ML model fraud probability [0.0, 1.0] |
| `ml_points` | `FLOAT` | Default `0.0`, Not Null | ML point contribution (max 60.0) |
| `rule_points` | `FLOAT` | Default `0.0`, Not Null | Scaled behavioural rule penalty points (max 40.0) |
| `recommended_action` | `TEXT` | Not Null | Prescribed operational mitigation |
| `summary` | `TEXT` | Not Null | Executive natural language explanation |
| `reasons` | `JSON` | Nullable | Full itemized array of triggered signals, details, and points |
| `features` | `JSON` | Nullable | 11-element feature vector passed to ML classifier |
| `created_at` | `TIMESTAMP WITH TZ` | Server Default `NOW()` | Timestamp when record was written to database |

### 2.2 Table Indexes
- **Primary Index**: `id`
- **Unique Index**: `transaction_id`
- **User Index**: `user_id`
- **Timestamp Index**: `timestamp`
- **Composite Behavioral Index**: `Index("ix_transactions_user_timestamp", "user_id", "timestamp")` optimizes chronological lookups of previous user activity.

---

## 3. How Behavioral Context Is Calculated

When a transaction scoring request arrives at `POST /api/v1/transactions/score`:

```
Incoming Request (amount, user_id, device_id, location, timestamp)
                                  ↓
Query Database for user_id past transactions ordered by timestamp DESC
                                  ↓
                  Does past transaction history exist?
                 /                                    \
             YES                                       NO (Cold Start)
              ↓                                         ↓
- prev_txn = past_txns[0]                      - seconds_since_prev = client input or 86400.0
- seconds_since_prev = max(0, t - prev.t)      - txn_count_10min = client input or 1
- txn_count_10min = txns in last 600s + 1      - txn_count_1h = client input or 1
- txn_count_1h = txns in last 3600s + 1        - is_new_device = client input or 0
- is_new_device = 1 if dev not in past else 0  - is_new_location = client input or 0
- is_new_location = 1 if loc not in past else 0- profile = default_profile() or pre-loaded demo
- profile = dynamic profile from DB history
                                  ↓
                 Pass to Existing FraudScope Engine
                 (features_from_transaction + model.predict_proba)
                                  ↓
                 Pass to Existing Risk Engine
                 (score_risk: 60% ML + 40% Rules)
                                  ↓
                 Persist Transaction + Scoring Outcome to DB
                                  ↓
                 Return Structured JSON Response
```

### 3.1 Velocity and Time-Delta Derivation
1. **Trailing 10-Minute Velocity (`txn_count_10min`)**:
   $$\text{cutoff}_{10m} = \text{current\_timestamp} - 600$$
   $$\text{txn\_count\_10min} = \sum_{t \in \text{past\_txns}} \mathbb{I}(t.\text{timestamp} \ge \text{cutoff}_{10m}) + 1$$
2. **Elapsed Time Delta (`seconds_since_prev`)**:
   $$\text{seconds\_since\_prev} = \max\left(0.0, \text{current\_timestamp} - \text{past\_txns}[0].\text{timestamp}\right)$$
3. **Novelty Verification**:
   - `known_devices = {t.device_id for t in past_txns}`
   - `is_new_device = 1 if device_id not in known_devices else 0`
   - `known_locations = {t.location for t in past_txns}`
   - `is_new_location = 1 if location not in known_locations else 0`

### 3.2 Cold-Start Behavior
For a brand-new user with zero prior transactions in PostgreSQL:
- The system safely identifies that no historical records exist.
- It does **not** invent artificial history.
- The existing [`default_profile()`](file:///c:/Users/user/OneDrive/Documents/Documents/PROJECT/FRAUDSCOPE-AI/FRAUDSCOPE-AI/src/features.py#L148-L157) in `src/features.py` is utilized, which informs the risk engine to label the baseline comparison as approximate and flags a `"Thin customer history"` (+4.0 pts) factor.
- For backward compatibility with the demo scenario, if a client explicitly provides demo parameters (`txn_count_10min: 7, seconds_since_prev: 120`), they are respected when zero history exists. Once transactions are persisted, subsequent requests strictly use database-derived metrics.

---

## 4. API Endpoints

### 4.1 `GET /health`
Returns service status and database connectivity without exposing connection strings or credentials.
```json
{
  "status": "ok",
  "database": "connected"
}
```

### 4.2 `POST /api/v1/transactions/score`
Scores a financial transaction using database context and persists the assessment.

**Sample Request:**
```json
{
  "user_id": "C123",
  "amount": 85000,
  "hour": 2,
  "device_id": "device_new",
  "location": "Delhi"
}
```

**Sample Response:**
```json
{
  "transaction_id": "TXN-02A04F64",
  "risk_score": 91,
  "risk_level": "HIGH",
  "ml_probability": 0.8844,
  "ml_points": 53.1,
  "rule_points": 38.0,
  "reasons": [
    {
      "signal": "Model pattern similarity",
      "detail": "The model rates this transaction 88.4% similar to known fraudulent behaviour.",
      "points": 53.1
    },
    {
      "signal": "Unusually high amount",
      "detail": "Rs85,000 is 34.0x a default assumed baseline. This customer has no transaction history yet, so this comparison is approximate, not a learned pattern.",
      "points": 14.0
    },
    {
      "signal": "Unusual transaction time",
      "detail": "Executed at 02:00, inside the customer's normal inactive window.",
      "points": 8.0
    },
    {
      "signal": "Thin customer history",
      "detail": "Very little past activity, so behavioural baselines are weak.",
      "points": 4.0
    }
  ],
  "summary": "Risk 91/100 (HIGH). Flagged because of unusually high amount; unusual transaction time; thin customer history. Recommended action: Hold for additional verification and route to a fraud analyst.",
  "recommended_action": "Hold for additional verification and route to a fraud analyst.",
  "user_id": "C123",
  "features": { ... }
}
```

### 4.3 `GET /api/v1/transactions/{transaction_id}`
Retrieves a previously stored transaction along with its risk score, reasons, and features.

### 4.4 `GET /api/v1/users/{user_id}/transactions?limit=20&skip=0`
Retrieves paginated chronological transactions and risk scores for a given user.

---

## 5. Configuration & Environment Variables

Create a `.env` file in `backend/` or the project root (see [`.env.example`](file:///c:/Users/user/OneDrive/Documents/Documents/PROJECT/FRAUDSCOPE-AI/FRAUDSCOPE-AI/.env.example)):

```bash
# PostgreSQL Database Connection URL
DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/fraudscope_db

# Host and Port
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

# CORS Allowed Origins
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

*Note: If `DATABASE_URL` is omitted, the application automatically defaults to `sqlite:///./fraudscope.db` in the repository root, ensuring zero-friction local execution without requiring a pre-configured database server.*

---

## 6. How to Start the Backend & Run Tests

### 6.1 Start the FastAPI Server
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive Documentation:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 6.2 Run the Phase 3 Test Suite
The comprehensive test suite tests database connectivity, persistence, transaction scoring, retrieval, velocity derivation, cold-start handling, and validation:

```powershell
python -m unittest backend.tests.test_phase3_db -v
```

### 6.3 Run the Streamlit Prototype
The existing Streamlit application continues to function independently:
```powershell
python -m streamlit run dashboard/app.py
```
