# FRAUDSCOPE AI — Comprehensive Architecture & Pipeline Audit

**Document Version:** 1.0.0  
**Audit Date:** September 2026  
**Target Project:** FRAUDSCOPE AI (Explainable Real-Time Financial Fraud Intelligence & Risk Scoring Platform)  
**Status:** Audit Completed — Baseline Established (No source modifications permitted)

---

## Executive Summary

FRAUDSCOPE AI is an explainable fraud intelligence platform that evaluates incoming financial transactions and outputs a composite risk score (0–100), risk tier (`LOW`, `MEDIUM`, `HIGH`), granular behavioural factor breakdown, and a recommended operational action.

The repository contains a fully functional, self-contained ML prototype featuring:
- **Canonical data preprocessing** supporting both the real Kaggle IEEE-CIS dataset and an autonomous synthetic transaction simulator.
- **Chronological, leakage-free behavioural feature engineering** that constructs dynamic customer profiles.
- **Gradient-boosted decision trees** (`HistGradientBoostingClassifier`) with class imbalance weighting and precision–recall curve threshold optimization.
- **A dual-component hybrid risk engine** combining ML statistical pattern recognition (60% weight) with deterministic, auditable behavioural rules (40% weight).
- **A Streamlit-based analyst dashboard** featuring single-transaction scoring, an interactive alert queue, and model performance auditing.

This audit provides a comprehensive structural, algorithmic, and architectural inspection of the codebase to establish the baseline for migrating from the single-process Streamlit prototype to an enterprise-grade full-stack architecture powered by **FastAPI**, **PostgreSQL**, and **React**.

---

## 1. Current System Architecture

The existing prototype runs entirely as a single-process local Python application. Streamlit serves as both the application server and the presentation layer, directly loading ML model artifacts into process memory.

### 1.1 Architecture Topology (As-Is)

```
+-------------------------------------------------------------------------------+
|                             Streamlit Process (dashboard/app.py)              |
|                                                                               |
|  +------------------------+  +---------------------+  +--------------------+  |
|  | Tab 1: Single Scoring  |  | Tab 2: Alert Queue  |  | Tab 3: Model Perf  |  |
|  +-----------+------------+  +----------+----------+  +---------+----------+  |
|              |                          |                       |             |
|              | In-Memory Function Call  | Batch Simulation      | Reads       |
|              v                          v                       v             |
|  +-------------------------------------------------+  +--------------------+  |
|  |          FraudScope Predictor Instance          |  |  load_metrics()    |  |
|  |               (src/predictor.py)                |  |   (src/model.py)   |  |
|  |                                                 |  +---------+----------+  |
|  |  - features_from_transaction()                  |            |             |
|  |  - predict_proba()                              |            |             |
|  |  - score_risk()                                 |            |             |
|  +-------+-----------------------------+-----------+            |             |
+----------|-----------------------------|------------------------|-------------+
           |                             |                        |
           v                             v                        v
+----------------------+     +----------------------+   +-------------------+
| models/fraud_model.pkl |   | models/profiles.json |   | models/metrics.json |
| (Trained Scikit-Learn|     | (Pre-computed User   |   | (Model Validation |
|  Gradient Boosting)  |     |  Historical Profiles)|   |  Scores & Matrix) |
+----------------------+     +----------------------+   +-------------------+
```

### 1.2 Component Summary
- **Data Ingestion & Preprocessing (`src/preprocessing.py`)**: Standardizes diverse inputs into a canonical schema.
- **Feature Engineering (`src/features.py`)**: Computes customer-centric deviation metrics without temporal leakage.
- **Model Training & Evaluation (`src/model.py`)**: Trains `HistGradientBoostingClassifier` and persists model and validation metrics.
- **Risk & Explanation Engine (`src/risk_engine.py`)**: Blends probabilistic ML inference with auditable business heuristics.
- **Unified Predictor Facade (`src/predictor.py`)**: Encapsulates model inference, profile matching, and risk evaluation into a single entrypoint.
- **Presentation Layer (`dashboard/app.py`)**: Renders interactive UI, scenario presets, alert triage queues, and performance metrics.

---

## 2. Current ML Pipeline

The ML lifecycle is divided into three distinct operational stages: Training, Profile Generation, and Real-Time Inference.

```
+--------------------------------------------------------------------------------+
|                             OFFLINE / TRAINING PIPELINE                        |
+--------------------------------------------------------------------------------+
  [IEEE-CIS Raw CSV / Synthetic Generator]
                     |
                     v
          src/preprocessing.py::build_events()
          - Canonical schema adaptation
          - Cleaning, validation, timestamp sort
                     |
                     v
          data/processed/events.csv (Canonical event logs)
                     |
                     v
          src/features.py::build_features()
          - Single-pass chronological feature aggregation
          - Running profile state accumulation (sum, sumsq, devices, locations)
                     |
        +------------+------------+
        |                         |
        v                         v
  data/processed/features.csv   models/profiles.json (Top 500 customer baselines)
        |
        v
  src/model.py::train()
  - Chronological time-split (80% train, 20% test)
  - Class-weighted HistGradientBoostingClassifier training
  - Optimal threshold selection via Precision-Recall curve
  - Permutation feature importance extraction
        |
        +-----------------------------+
        |                             |
        v                             v
  models/fraud_model.pkl       models/metrics.json


+--------------------------------------------------------------------------------+
|                         ONLINE / SCORING INFERENCE PIPELINE                    |
+--------------------------------------------------------------------------------+
  Incoming Transaction Payload + User ID
                     |
                     v
          src/predictor.py::FraudScope.score()
                     |
                     +---> Profile Lookup (models/profiles.json or default_profile())
                     |
                     v
          src/features.py::features_from_transaction()
          - Normalizes amount against user baseline
          - Checks new device / new location flags
          - Computes velocity and night-time indicators
                     |
                     v
          ML Inference: HistGradientBoostingClassifier.predict_proba()
          - Probability output: [0.0, 1.0]
                     |
                     v
          src/risk_engine.py::score_risk()
          - ML Component = Probability * 60.0
          - Heuristic Rules Evaluation = Sum of rule penalties (capped at 40.0)
          - Final Score = min(round(ML + Rules), 100)
                     |
                     v
          Output Payload: Score (0-100), Level (LOW/MED/HIGH), Action, Reasons, Summary
```

### 2.1 Chronological Split Strategy
Unlike standard random K-fold splits, the pipeline uses **chronological splitting** (`time_split` at 80% index). Transactions are sorted by timestamp:
- **Training Set (First 80%)**: Represents historical transactions.
- **Testing Set (Final 20%)**: Represents future unseen transactions.
This avoids temporal leakage where future customer behavior is inadvertently used to evaluate historical transactions.

---

## 3. Input / Output Specifications of Each ML Module

### 3.1 `src/preprocessing.py`

#### Responsibilities:
- Ingests raw data or dynamically simulates realistic financial transactions.
- Enforces the strict 6-column **Canonical Schema**:
  1. `user_id` (str): Customer/card identifier.
  2. `timestamp` (int): Unix epoch seconds or relative chronological seconds.
  3. `amount` (float): Transaction value in currency units.
  4. `device_id` (str): Hardware/browser client fingerprint.
  5. `location` (str): Geographic city or billing region.
  6. `is_fraud` (int): Binary target label (0 = Legitimate, 1 = Fraudulent).

#### Core Functions:
| Function | Inputs | Outputs | Description |
|---|---|---|---|
| `load_raw(path, identity_path, nrows)` | `path: str`, `identity_path: str`, `nrows: int \| None` | `pd.DataFrame \| None` | Reads IEEE-CIS `train_transaction.csv` and merges `train_identity.csv` on `TransactionID` if present. Returns `None` if missing. |
| `adapt_ieee(df)` | `df: pd.DataFrame` (IEEE-CIS raw) | `pd.DataFrame` (Canonical) | Derives `user_id` proxy (`"C" + card1 + "_" + addr1`), maps `TransactionDT` to `timestamp`, `TransactionAmt` to `amount`, builds device fingerprint, and extracts location. |
| `generate_synthetic(n_users, txns_per_user, fraud_rate, seed)` | `n_users: int = 1200`, `txns_per_user: int = 40`, `fraud_rate: float = 0.025`, `seed: int = 42` | `pd.DataFrame` (Canonical) | Simulates transactions with diurnal probability distribution (`_daytime_profile`), log-normal amount distribution, burst velocities, and correlated fraud signals. |
| `clean(events)` | `events: pd.DataFrame` | `pd.DataFrame` | Drops nulls in `user_id`, `timestamp`, `amount`; ensures `amount > 0`; fills missing string identifiers; sorts by `timestamp`. |
| `build_events(use_synthetic, nrows, save)` | `use_synthetic: bool`, `nrows: int \| None`, `save: bool` | `pd.DataFrame` | Master preprocessor; outputs `data/processed/events.csv`. |

---

### 3.2 `src/features.py`

#### Responsibilities:
- Computes 11 behavioural features comparing each transaction against the customer's historical baseline.
- Generates and persists customer profile baselines (`models/profiles.json`).
- Exposes `features_from_transaction()` for identical scoring-time feature extraction.

#### Generated Features (`FEATURE_COLUMNS`):
1. `log_amount`: `np.log1p(amount)` — Log-transformed raw amount.
2. `amount_ratio`: `amount / (customer_mean + 1.0)` — Relative size against baseline.
3. `amount_zscore`: `(amount - customer_mean) / (customer_std + 1.0)` — Number of standard deviations above baseline.
4. `hour`: `(timestamp // 3600) % 24` — Hour of the day (0–23).
5. `is_night`: Binary flag (1 if hour in `{0, 1, 2, 3, 4, 5}`, else 0).
6. `seconds_since_prev`: Elapsed seconds since previous transaction (default `86400.0`).
7. `txn_count_10min`: Transaction frequency within the trailing 10 minutes (600s).
8. `txn_count_1h`: Transaction frequency within the trailing 1 hour (3600s).
9. `is_new_device`: Binary flag (1 if `n > 0` and `device_id` was not previously used by customer).
10. `is_new_location`: Binary flag (1 if `n > 0` and `location` was not previously used by customer).
11. `user_txn_index`: Prior transaction count `n`, quantifying baseline statistical maturity.

#### Core Functions:
| Function | Inputs | Outputs | Description |
|---|---|---|---|
| `build_features(events, save)` | `events: pd.DataFrame`, `save: bool` | `tuple[pd.DataFrame, pd.Series, dict]` `(X, y, profiles)` | Single chronological pass; computes feature matrix `X`, label vector `y`, and extracts profile states. Saves `features.csv` and `profiles.json`. |
| `_finalise_profiles(state, max_users)` | `state: dict`, `max_users: int = 500` | `dict` | Filters to the top 500 most active customers, computing `txn_count`, `mean_amount`, `std_amount`, `known_devices`, and `known_locations`. |
| `default_profile()` | None | `dict` | Cold-start profile for unknown users: `mean_amount=2500.0`, `std_amount=1500.0`, empty device/location lists. |
| `features_from_transaction(txn, profile)` | `txn: dict`, `profile: dict \| None` | `pd.DataFrame` (1 row, 11 columns) | Synchronous scoring-time feature extraction matching training definitions. |

---

### 3.3 `src/model.py`

#### Responsibilities:
- Trains the machine learning model on historical feature sets.
- Implements class rebalancing for extreme fraud skew.
- Determines optimal classification threshold via the Precision–Recall curve.
- Evaluates test metrics and computes permutation feature importances.
- Serializes trained artifacts to `models/fraud_model.pkl` and `models/metrics.json`.

#### Model Architecture:
- **Algorithm**: `sklearn.ensemble.HistGradientBoostingClassifier`
- **Configuration**:
  - `max_iter`: 300
  - `learning_rate`: 0.06
  - `max_depth`: 6
  - `min_samples_leaf`: 40
  - `l2_regularization`: 1.0
  - `early_stopping`: True (`validation_fraction=0.1`)
  - `random_state`: 42
  - `class_weight`: `{0: 1.0, 1: pos_weight}` where `pos_weight = (len(y_train) - pos) / pos`

#### Core Functions:
| Function | Inputs | Outputs | Description |
|---|---|---|---|
| `time_split(X, y, test_size)` | `X: pd.DataFrame`, `y: pd.Series`, `test_size: float = 0.2` | `X_train, X_test, y_train, y_test` | Chronological cut at index `len(X) * (1 - test_size)`. |
| `build_model(pos_weight)` | `pos_weight: float` | `HistGradientBoostingClassifier` | Instantiates classifier with balancing weights. |
| `evaluate(model, X_test, y_test)` | `model`, `X_test`, `y_test` | `dict` | Computes precision, recall, F1, PR-AUC, ROC-AUC, threshold, and confusion matrix. |
| `permutation_importance_fast(model, X_test, y_test, n_repeats)` | `model`, `X_test`, `y_test`, `n_repeats: int = 3` | `dict[str, float]` | Measures PR-AUC score degradation when each column is permuted. |
| `train(use_synthetic, nrows, importance)` | `use_synthetic: bool`, `nrows: int \| None`, `importance: bool` | `tuple[model, dict]` | Complete training loop; writes `models/fraud_model.pkl` and `models/metrics.json`. |
| `load_metrics(path)` | `path: str` | `dict` | Loads validation results from `models/metrics.json`. |

---

### 3.4 `src/risk_engine.py`

#### Responsibilities:
- Converts probabilistic ML predictions into explainable, analyst-ready risk scores (0–100).
- Applies deterministic, auditable heuristic rules.
- Allocates point contributions and dynamically normalizes rule penalties when exceeding the rule budget.
- Generates natural language reason summaries.

#### Core Data Structures:
```python
@dataclass
class Reason:
    signal: str      # e.g., "Unusually high amount"
    detail: str      # Contextual natural language explanation
    points: float    # Scaled points added to composite score

@dataclass
class RiskResult:
    score: int              # Composite risk score (0 - 100)
    level: str              # "LOW" | "MEDIUM" | "HIGH"
    action: str             # Prescribed operational mitigation
    ml_probability: float   # Raw model output [0.0, 1.0]
    ml_points: float        # ML contribution (max 60.0)
    rule_points: float      # Rule contribution (max 40.0)
    reasons: list[Reason]   # Itemized factor breakdown
```

#### Core Functions:
| Function | Inputs | Outputs | Description |
|---|---|---|---|
| `_rule_reasons(f, txn)` | `f: dict` (features), `txn: dict` (raw txn) | `list[Reason]` | Evaluates 7 behavioural heuristic rules. |
| `score_risk(ml_probability, features, txn)` | `ml_probability: float`, `features: dict`, `txn: dict \| None` | `RiskResult` | Computes weighted score: `ml_points + rule_points`, scales rules if raw points exceed 40.0, clamps to 100, assigns risk level. |
| `risk_level(score)` | `score: int` | `str` | Maps score to `LOW` (<=30), `MEDIUM` (31–70), or `HIGH` (71–100). |
| `explain_text(result)` | `result: RiskResult` | `str` | Produces an executive summary sentence for queues and notifications. |

---

### 3.5 `src/predictor.py`

#### Responsibilities:
- High-level facade integrating model deserialization, profile extraction, feature generation, ML inference, and risk engine execution.
- Primary interface for upstream clients (Streamlit dashboard and future FastAPI routers).

#### Class: `FraudScope`
| Method | Inputs | Outputs | Description |
|---|---|---|---|
| `load(model_path)` *(classmethod)* | `model_path: str` | `FraudScope` instance | Loads `fraud_model.pkl` via joblib and `profiles.json` via JSON parser. |
| `get_profile(user_id)` | `user_id: str \| None` | `dict` | Returns customer baseline profile or defaults to `default_profile()`. |
| `predict_proba(X)` | `X: pd.DataFrame` | `float` | Extracts required columns and returns probability of class 1 (Fraud). |
| `score(txn, user_id, profile)` | `txn: dict`, `user_id: str \| None`, `profile: dict \| None` | `dict` | End-to-end execution returning dictionary formatted `RiskResult` with features and summary. |
| `score_batch(transactions, user_ids)` | `transactions: list[dict]`, `user_ids: list[str] \| None` | `pd.DataFrame` | Scores a batch of transactions and sorts descending by risk score. |

---

## 4. Existing Model Artifacts

All model artifacts are stored under the `models/` directory:

### 4.1 `models/fraud_model.pkl`
A serialized Joblib archive with a dictionary structure:
```python
{
    "model": HistGradientBoostingClassifier(...),
    "feature_columns": [
        "log_amount", "amount_ratio", "amount_zscore", "hour", "is_night",
        "seconds_since_prev", "txn_count_10min", "txn_count_1h",
        "is_new_device", "is_new_location", "user_txn_index"
    ],
    "metadata": {
        "source": "synthetic",        # or "auto"
        "n_train": 41818,              # training sample size
        "threshold": 0.8921,          # F1-maximizing threshold
        "metrics": {
            "precision": 0.5000,
            "recall": 0.4737,
            "f1": 0.4865,
            "pr_auc": 0.4712,
            "roc_auc": 0.9393
        }
    }
}
```

### 4.2 `models/metrics.json`
Contains held-out test evaluation scores from the synthetic training baseline:
- `n_test`: 10,455
- `fraud_rate_test`: 2.73%
- `threshold`: 0.8921
- `precision`: 0.5000
- `recall`: 0.4737
- `f1`: 0.4865
- `pr_auc`: 0.4712
- `roc_auc`: 0.9393
- `confusion_matrix`:
  - True Negatives (`[0][0]`): 10,035
  - False Positives (`[0][1]`): 135
  - False Negatives (`[1][0]`): 150
  - True Positives (`[1][1]`): 135
- `feature_importance`:
  - `hour`: +0.28210
  - `is_new_device`: +0.17295
  - `amount_ratio`: +0.16189
  - `amount_zscore`: +0.09819
  - `log_amount`: +0.02749
  - `seconds_since_prev`: +0.02422
  - `is_new_location`: +0.00545
  - `user_txn_index`: +0.00147
  - `is_night`: +0.00096
  - `txn_count_10min`: -0.00019
  - `txn_count_1h`: -0.00055

### 4.3 `models/profiles.json`
Stores historical customer baseline distributions for up to 500 active users:
```json
{
  "U00372": {
    "txn_count": 83,
    "mean_amount": 830.78,
    "std_amount": 1250.35,
    "known_devices": ["android-b", "ios-a", "unk-3729", "unk-4674", "web-chrome", "web-edge"],
    "known_locations": ["Bengaluru", "Chennai", "Delhi", "Hyderabad", "Jaipur", "Nagpur"]
  }
}
```

---

## 5. Existing Risk Scoring Logic

The risk engine ensures that statistical pattern recognition is balanced with explainable, deterministic rules.

### 5.1 Scoring Formula
$$\text{Final Risk Score} = \min\left(\text{round}(\text{ML Points} + \text{Rule Points}), 100\right)$$

Where:
- $\text{ML Points} = \text{round}(\text{ML Probability} \times 60.0, 1)$  *(Maximum 60 points)*
- $\text{Rule Points} = \min(\sum \text{Raw Rule Points}, 40.0)$  *(Maximum 40 points)*

#### Proportional Rule Contribution Scaling:
When the sum of triggered heuristic rule points exceeds the 40.0 cap ($\text{Raw Rule Points} > 40.0$):
$$\text{Scale Factor} = \frac{40.0}{\sum \text{Raw Rule Points}}$$
$$\text{Individual Rule Points} = \text{round}(\text{Raw Points} \times \text{Scale Factor}, 1)$$
This ensures that the itemized breakdown shown to the fraud analyst sums exactly to the applied rule score.

### 5.2 Heuristic Rules Specification
| Rule Identifier | Trigger Condition | Points | Dynamic Contextual Reason |
|---|---|---|---|
| **Unusually High Amount** | `amount_ratio >= 6.0` | +14.0 pts | Contextualized by history depth: indicates whether baseline is assumed (`n=0`), low-confidence (`n<3`), or learned (`n>=3`). |
| **Elevated Amount** | `3.0 <= amount_ratio < 6.0` | +8.0 pts | Explains transaction is 3–6x normal spending. |
| **New Device** | `is_new_device == 1` | +10.0 pts | Flags device fingerprint never previously seen for user. |
| **Location Deviation** | `is_new_location == 1` | +10.0 pts | Flags city/region outside user's established locations. |
| **Unusual Transaction Time**| `is_night == 1` (`00:00 - 05:59`)| +8.0 pts | Flags execution inside normal customer sleep window. |
| **High Velocity** | `txn_count_10min >= 4` | +12.0 pts | Flags burst of 4+ transactions within 10 minutes. |
| **Elevated Velocity** | `txn_count_10min == 3` | +6.0 pts | Flags 3 transactions within 10 minutes. |
| **Rapid Repeat** | `seconds_since_prev < 60` | +5.0 pts | Flags transactions triggered under 60 seconds apart. |
| **Thin Customer History** | `user_txn_index < 3` | +4.0 pts | Alerts analyst that baseline is supported by <3 transactions. |

### 5.3 Risk Levels and Recommended Actions
| Risk Tier | Score Range | Default Operational Action |
|---|---|---|
| **LOW** | 0 – 30 | Allow — no action needed. |
| **MEDIUM** | 31 – 70 | Step-up verification (OTP / app confirmation) before approving. |
| **HIGH** | 71 – 100 | Hold for additional verification and route to a fraud analyst. |

---

## 6. Existing Streamlit Flow

`dashboard/app.py` operates as an interactive presentation prototype structured into three tabs:

### 6.1 Initialization & Caching
- **Engine Singleton**: `get_engine()` decorated with `@st.cache_resource` loads `FraudScope.load()` once per server process.
- **Metrics Cache**: `get_metrics()` decorated with `@st.cache_data` caches `load_metrics()`.
- **Session State**: Maintains `st.session_state["alert_log"]` as an in-memory list of analyst-flagged transactions.

### 6.2 Tab Breakdown
1. **Tab 1: "Score a transaction"**:
   - Offers scenario presets (`Normal purchase`, `Suspicious - elevated amount only`, `Travelling customer`, `Account takeover`).
   - Customer profile selector populates baseline data.
   - User inputs: Amount, Hour slider (0–23), Location dropdown, Device dropdown, New Device checkbox, New Location checkbox, 10-minute Velocity slider (1–12), and Seconds Since Previous input.
   - Defensive validation via `validate_transaction()`.
   - Calls `engine.score()`.
   - Renders visual score card, progress bar, risk tier badge, action recommendation, breakdown reasons, and feature vector expander.
   - "Add this transaction to Alert Queue" pushes record to `st.session_state["alert_log"]`.
2. **Tab 2: "Alert queue"**:
   - Calls `simulate_batch(n=40)` to generate a randomized incoming transaction batch scored via `engine.score_batch()`.
   - Merges live flagged alerts with simulated batch.
   - Computes KPI metric cards (HIGH, MEDIUM, LOW counts).
   - Provides multi-select filters for risk level and source (`Live` vs `Simulated`).
3. **Tab 3: "Model performance"**:
   - Displays training metadata (dataset source, training count, decision threshold).
   - Renders metric cards: Precision, Recall, F1-Score, PR-AUC, ROC-AUC.
   - Renders 2x2 confusion matrix dataframe.
   - Renders horizontal bar chart of permutation feature importances.

---

## 7. Components that Can Be Reused by FastAPI

The modular design of `src/` enables immediate reuse within a FastAPI backend:

| Component / File | Reusability | FastAPI Role / Integration Strategy |
|---|---|---|
| `src/predictor.py` (`FraudScope`) | **100% Direct Reuse** | Instantiate as an application-state singleton inside FastAPI `lifespan` handler (`app.state.fraudscope = FraudScope.load()`). |
| `src/risk_engine.py` (`score_risk`, `explain_text`, `RiskResult`, `Reason`) | **100% Direct Reuse** | Core business logic layer. Invoked by service layer to generate scores and explanation objects. |
| `src/features.py` (`features_from_transaction`, `default_profile`) | **100% Direct Reuse** | Request feature transformation engine. Transforms incoming Pydantic schema + DB customer profile into feature DataFrame. |
| `src/model.py` (`load_metrics`) | **100% Direct Reuse** | System health and observability router (`GET /api/v1/metrics`). |
| `models/fraud_model.pkl` | **100% Direct Reuse** | Pickled model artifact mounted directly into the inference container. |
| `models/profiles.json` | **Seed Data / Cache** | Initial seed data for populating PostgreSQL `customer_profiles` table. |
| `models/metrics.json` | **Read-Only Artifact** | Static metadata response for dashboard telemetry. |

---

## 8. Components that Should Remain Unchanged

To maintain ML integrity, the following components must not be modified:
1. **Model Weights & Serialization (`models/fraud_model.pkl`)**: Must remain intact. Re-training or modifying parameter definitions risks breaking existing scoring behavior.
2. **Core Feature Computation Math (`src/features.py`)**: The mathematical formulas for `log_amount`, `amount_ratio`, `amount_zscore`, and time/velocity indicators must remain identical to ensure training-serving consistency.
3. **Dual-Component Scoring Split (`src/risk_engine.py`)**: The 60-point ML / 40-point rule allocation, threshold bounds (30/70/100), and proportional penalty scaling represent the core domain logic.
4. **Natural Language Explanation Generation (`src/risk_engine.py`)**: The human-readable reason strings and executive summary logic provide explainability.
5. **Preprocessing Schema Standard (`src/preprocessing.py`)**: The 6-column canonical event schema (`user_id, timestamp, amount, device_id, location, is_fraud`).

---

## 9. Technical Debt and Prototype Limitations

While effective as a standalone prototype, several design limitations must be addressed when migrating to a production system:

1. **Volatile In-Memory Session State**:
   - In Streamlit, flagged alerts in `st.session_state.alert_log` are lost upon page reload or container restart. There is no durable persistence.
2. **Static Profile Store (`profiles.json`)**:
   - Profiles are pre-computed for only 500 customers and stored in a static JSON file.
   - When a transaction occurs, the customer's profile is not updated in real time (transaction count, running mean, running sum of squares, and device/location sets remain static).
3. **Manual Feature Inputs in UI**:
   - In `dashboard/app.py`, velocity (`txn_count_10min`) and time delta (`seconds_since_prev`) are passed via manual sliders. In production, these must be computed automatically from the customer's transaction history in PostgreSQL.
4. **Single-Process Coupling**:
   - Streamlit couples the presentation layer, ML inference, and data state in a single Python process. A long-running inference or batch simulation blocks UI responsiveness.
5. **Cold-Start Hardcoding**:
   - `default_profile()` assumes fixed defaults (`mean=2500.0`, `std=1500.0`). Cold-start customers should be dynamically flagged and baselines calibrated against global cohort statistics.
6. **Lack of Security & Multi-Tenancy**:
   - No authentication, role-based access control (RBAC), API keys, or audit logging exist in the prototype.
7. **Pickle Environment Sensitivity**:
   - `models/fraud_model.pkl` relies on standard `joblib` pickling, making it vulnerable to minor version mismatches in `scikit-learn`.

---

## 10. Proposed Migration Architecture for Full-Stack System

### 10.1 System Architecture Flow

The target full-stack architecture separates presentation, API orchestration, ML inference, and persistence:

```
+-------------------------------------------------------------------------------+
|                             CLIENT / PRESENTATION LAYER                       |
|                                                                               |
|             React Frontend (Vite + Tailwind CSS + Lucide + Recharts)          |
|  - Real-time Transaction Simulator                                            |
|  - Prioritized Analyst Alert Queue (Sort/Filter/Investigate)                 |
|  - Decision Disposition Workflow (Approve / Step-Up / Reject)                |
|  - Model Metrics & Explainability Visualizer                                 |
+---------------------------------------+---------------------------------------+
                                        |
                                        | HTTPS / REST JSON APIs
                                        v
+-------------------------------------------------------------------------------+
|                             API GATEWAY & BACKEND LAYER                       |
|                                                                               |
|                               FastAPI Backend                                 |
|  - CORS, Auth & Role-Based Access Control                                     |
|  - Pydantic Request / Response Validation                                     |
|  - REST Endpoints: /transactions, /alerts, /metrics, /profiles                |
+---------------------------------------+---------------------------------------+
                                        |
                                        | Dependency Injection
                                        v
+-------------------------------------------------------------------------------+
|                             APPLICATION SERVICE LAYER                         |
|                                                                               |
|                            Transaction Service                                |
|  1. Fetch customer historical baseline & recent txns from PostgreSQL          |
|  2. Calculate dynamic velocity (txn_count_10min, seconds_since_prev)          |
|  3. Detect new device / new location automatically from DB profile            |
|  4. Assemble payload & invoke FraudScope ML Engine                            |
|  5. Forward ML probabilities to Risk Engine                                   |
|  6. Persist transaction, features, risk scores, and alert to PostgreSQL       |
|  7. Update customer profile online (mean, variance, device/location sets)     |
+-------------------+---------------------------------------+-------------------+
                    |                                       |
                    v                                       v
+---------------------------------------+   +-----------------------------------+
|          EXISTING ML ENGINE           |   |            RISK ENGINE            |
|                                       |   |                                   |
|     src/predictor.py (FraudScope)     |   |         src/risk_engine.py        |
|  - Feature extraction                 |   |  - Rule evaluation                |
|  - Scikit-Learn predict_proba()       |   |  - Proportional penalty scaling   |
|  - Unchanged models/fraud_model.pkl   |   |  - Natural language explanation   |
+---------------------------------------+   +-----------------------------------+
                    |                                       |
                    +-------------------+-------------------+
                                        |
                                        | Async SQLAlchemy / SQLModel
                                        v
+-------------------------------------------------------------------------------+
|                             PERSISTENCE LAYER (PostgreSQL)                    |
|                                                                               |
|  - customer_profiles (user_id, txn_count, mean_amt, sum_sq, devices, locs)    |
|  - transactions (id, user_id, amount, timestamp, device_id, location, status) |
|  - risk_assessments (id, txn_id, score, level, action, ml_points, rule_points)|
|  - alert_queue (id, assessment_id, status, assigned_analyst, notes)           |
+-------------------------------------------------------------------------------+
```

### 10.2 PostgreSQL Relational Data Schema

```sql
-- 1. Customer Profiles Table
CREATE TABLE customer_profiles (
    user_id VARCHAR(64) PRIMARY KEY,
    txn_count INTEGER NOT NULL DEFAULT 0,
    mean_amount NUMERIC(12, 2) NOT NULL DEFAULT 2500.00,
    sum_amount NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    sum_sq_amount NUMERIC(18, 2) NOT NULL DEFAULT 0.00,
    std_amount NUMERIC(12, 2) NOT NULL DEFAULT 1500.00,
    known_devices JSONB NOT NULL DEFAULT '[]'::jsonb,
    known_locations JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Transactions Table
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(64) REFERENCES customer_profiles(user_id),
    amount NUMERIC(12, 2) NOT NULL,
    timestamp BIGINT NOT NULL,
    device_id VARCHAR(128) NOT NULL,
    location VARCHAR(128) NOT NULL,
    currency VARCHAR(10) DEFAULT 'Rs',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Risk Assessments Table
CREATE TABLE risk_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    score INTEGER NOT NULL CHECK (score >= 0 AND score <= 100),
    level VARCHAR(16) NOT NULL CHECK (level IN ('LOW', 'MEDIUM', 'HIGH')),
    action TEXT NOT NULL,
    ml_probability NUMERIC(6, 4) NOT NULL,
    ml_points NUMERIC(5, 1) NOT NULL,
    rule_points NUMERIC(5, 1) NOT NULL,
    summary TEXT NOT NULL,
    reasons JSONB NOT NULL,
    feature_vector JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Analyst Alert Queue Table
CREATE TABLE alert_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES risk_assessments(id) ON DELETE CASCADE,
    source VARCHAR(32) NOT NULL DEFAULT 'Live',
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'INVESTIGATING', 'APPROVED', 'BLOCKED')),
    assigned_to VARCHAR(64),
    analyst_notes TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_user_time ON transactions(user_id, timestamp DESC);
CREATE INDEX idx_alerts_status_created ON alert_queue(status, created_at DESC);
CREATE INDEX idx_assessments_level ON risk_assessments(level);
```

### 10.3 FastAPI Endpoint Specifications

| HTTP Method | Route | Description |
|---|---|---|
| `POST` | `/api/v1/transactions/score` | Primary ingestion endpoint. Ingests raw transaction, enriches with historical context via DB, scores via ML/Risk engine, persists record, updates user profile, and returns comprehensive risk decision. |
| `GET` | `/api/v1/alerts` | Returns prioritized alert queue supporting status, tier, date, and source filtering with pagination. |
| `PATCH` | `/api/v1/alerts/{alert_id}` | Analyst triage action (update status to `APPROVED`, `BLOCKED`, `INVESTIGATING` with notes). |
| `GET` | `/api/v1/profiles/{user_id}` | Retrieves customer baseline profile, known devices, locations, and transaction history. |
| `GET` | `/api/v1/metrics` | Serves model validation metrics, confusion matrix, and feature importances from `models/metrics.json`. |
| `POST` | `/api/v1/transactions/batch-simulate` | Simulates an incoming batch of transactions for demonstration and load verification. |

### 10.4 React Frontend Architecture
- **Framework**: React 18+ with Vite and TypeScript.
- **Styling**: Tailwind CSS for responsive design matching the clean typography and card layouts of the prototype.
- **Iconography**: Lucide React.
- **Data Visualization**: Recharts for confusion matrix, score distribution histograms, and permutation feature importance bars.
- **State Management**: TanStack Query (React Query) for server-state caching and real-time polling.
- **Primary Views**:
  1. **Live Transaction Evaluator**: Interactive scenario tester with real-time risk gauges and reason trees.
  2. **Fraud Analyst Command Center**: Sortable alert queue with batch actions, risk badges, and detailed investigation drawer.
  3. **Customer 360 Profile Explorer**: Profile baseline viewer showing historical spending patterns, device rosters, and location breadcrumbs.
  4. **Model Performance & Governance Dashboard**: Confusion matrix, ROC/PR curves, and feature importance rankings.

---

## 11. Conclusion & Next Steps

This audit establishes that the existing ML prototype is technically sound, modular, and well-structured for migration. 
- The ML modules (`src/preprocessing.py`, `src/features.py`, `src/model.py`, `src/predictor.py`, `src/risk_engine.py`) and model artifacts (`models/`) can be integrated directly into FastAPI without altering their internal logic.
- The next development phases should proceed as follows:
  1. **Phase 1**: Configure database schemas and migrations in PostgreSQL.
  2. **Phase 2**: Implement the FastAPI backend and Transaction Service, wrapping the existing ML engine.
  3. **Phase 3**: Develop the modern React frontend.
  4. **Phase 4**: End-to-end integration and system verification.
