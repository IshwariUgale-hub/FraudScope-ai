# FRAUDSCOPE AI — Project Design Report (PDR)

## 1. Problem
Digital payment volumes are growing faster than the ability to review them manually. A
transaction can look unusual for many reasons — a large amount, a new device, a different
city, an odd hour, a burst of activity — but **unusual is not the same as fraudulent**. A
customer who normally transacts in Pune may travel to Delhi and buy a laptop for ₹80,000.
The real problem is not "fraud or not fraud"; it is *estimating risk and justifying it* so a
human can act.

## 2. Objective
For every transaction, produce:
1. a risk score between 0 and 100,
2. a risk level (LOW / MEDIUM / HIGH),
3. the specific signals that drove the score,
4. a recommended action.

## 3. Architecture
```
Historical dataset → Preprocessing → Feature engineering → ML model
        → Risk engine (ML + behavioural rules) → Risk score + explanation → Dashboard / alert
```
A simulated or live transaction joins the flow at the feature-engineering stage, using the
stored customer profile as its baseline.

## 4. Data
- **Primary**: public fraud-detection dataset (IEEE-CIS `train_transaction.csv`, optionally
  merged with `train_identity.csv`).
- **Fallback**: a built-in behavioural simulator, so the prototype is demonstrable without
  any download.
- Both are converted to one canonical schema:
  `user_id, timestamp, amount, device_id, location, is_fraud`.
- Known adaptation limits: IEEE-CIS has no explicit customer id (we use `card1 + addr1` as a
  card/billing proxy) and no device fingerprint unless the identity file is merged.

## 5. Features
| Feature | Signal it captures |
|---|---|
| `log_amount` | raw transaction size |
| `amount_ratio`, `amount_zscore` | size relative to *this customer's* own baseline |
| `hour`, `is_night` | activity outside the customer's normal window |
| `seconds_since_prev`, `txn_count_10min`, `txn_count_1h` | velocity / bursts |
| `is_new_device` | device never used by this customer |
| `is_new_location` | location outside the customer's usual set |
| `user_txn_index` | how much history supports the baseline |

All features are computed in a single chronological pass using only pre-transaction
information — no leakage.

## 6. Model
- Gradient-boosted decision trees (`HistGradientBoostingClassifier`), class-weighted to
  handle the imbalance.
- **Chronological** train/test split (train on the past, test on the future).
- Decision threshold selected from the precision–recall curve, not left at 0.5.

## 7. Risk engine
```
score = ML component (probability × 60)  +  behavioural rule points (capped at 40)
```
| Rule | Points |
|---|---|
| Amount 3×–6× / >6× the customer baseline | 8 / 14 |
| High velocity (≥4 txns in 10 min) | 12 |
| New device | 10 |
| Location deviation | 10 |
| Night-time transaction | 8 |
| Repeat within 60 seconds | 5 |
| Thin customer history | 4 |

Rule points are scaled proportionally when they exceed the cap, so displayed contributions
always add up to the score shown.

## 8. Evaluation
Accuracy is not reported. On an imbalanced fraud dataset a model that predicts "legitimate"
for everything scores above 97% accuracy while catching nothing. The prototype reports
precision, recall, F1, PR-AUC, ROC-AUC and the confusion matrix (`models/metrics.json`).

## 9. Differentiators
- Behavioural profiling per customer instead of global thresholds.
- Multi-signal scoring rather than a single rule.
- Explanation attached to every alert.
- Prioritisation: analysts work the queue top-down.

## 10. Prototype vs future
**Prototype**: historical dataset + ML model + simulated transaction input + Streamlit dashboard.
**Future**: real-time streaming, SHAP per-prediction explanations, graph-based detection of
fraud rings, continuous monitoring and drift alerts, secure APIs, federated learning.

## 11. Limitation
A suspicious transaction is not automatically fraudulent. FRAUDSCOPE AI supports
verification and investigation; it does not auto-block. False positives and false negatives
are expected and must be monitored.

## 12. One-line summary
> FRAUDSCOPE AI uses machine learning and behavioural signals to score suspicious financial
> transactions, explain why they are risky, and help fraud analysts prioritise them for
> verification.
