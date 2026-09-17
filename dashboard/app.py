"""
FRAUDSCOPE AI - Streamlit prototype dashboard.

Run from the project root:

    streamlit run dashboard/app.py

Three tabs:
  1. Score a transaction  - simulate one transaction and explain the score
  2. Alert queue          - a batch of simulated transactions, prioritised
  3. Model performance    - imbalanced-data metrics from the last training run
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import streamlit as st

# make `src` importable when Streamlit runs this file directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model import load_metrics                      # noqa: E402
from src.predictor import FraudScope                    # noqa: E402
from src.preprocessing import CITIES, DEVICES           # noqa: E402

st.set_page_config(page_title="FRAUDSCOPE AI", page_icon="", layout="wide")

LEVEL_COLORS = {"LOW": "#12A150", "MEDIUM": "#E8890C", "HIGH": "#D13438"}

st.markdown("""
<style>
  .fs-title   {font-size:2.1rem;font-weight:700;margin-bottom:0;}
  .fs-sub     {color:#6b7280;margin-top:.15rem;margin-bottom:1.2rem;}
  .fs-card    {border:1px solid #e5e7eb;border-radius:14px;padding:1.1rem 1.3rem;background:#fff;}
  .fs-score   {font-size:3.4rem;font-weight:800;line-height:1;}
  .fs-level   {display:inline-block;padding:.22rem .8rem;border-radius:999px;
               color:#fff;font-weight:700;letter-spacing:.04em;font-size:.85rem;}
  .fs-bar     {height:14px;border-radius:999px;background:#eef0f3;overflow:hidden;margin:.7rem 0 .2rem;}
  .fs-fill    {height:100%;border-radius:999px;}
  .fs-reason  {border-left:4px solid #d1d5db;padding:.5rem .8rem;margin-bottom:.5rem;background:#fafafa;}
  .fs-pts     {float:right;font-weight:700;color:#374151;}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_engine():
    return FraudScope.load()


def validate_transaction(amount, hour, velocity, gap) -> str | None:
    """Return a user-friendly error string, or None if the inputs are usable.

    The Streamlit widgets already clamp these ranges, so this is a defensive
    second check - e.g. if this function is ever called from somewhere other
    than the widgets below.
    """
    if amount is None or amount <= 0:
        return "Amount must be a positive number."
    if hour is None or not (0 <= hour <= 23):
        return "Hour must be between 0 and 23."
    if velocity is None or velocity < 1:
        return "Transactions in the last 10 minutes must be at least 1."
    if gap is None or gap < 0:
        return "Seconds since previous transaction cannot be negative."
    return None


@st.cache_data
def get_metrics():
    return load_metrics()


st.markdown('<p class="fs-title">FRAUDSCOPE AI</p>', unsafe_allow_html=True)
st.markdown('<p class="fs-sub">Explainable real-time financial fraud intelligence and risk scoring '
            '&nbsp;&middot;&nbsp; Detect. Explain. Prioritize. Protect.</p>', unsafe_allow_html=True)

try:
    engine = get_engine()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(
        "Could not load the trained model. This usually means it was trained with a "
        "different scikit-learn version than the one installed now.\n\n"
        f"Technical detail: {type(e).__name__}: {e}\n\n"
        "Fix: delete models/fraud_model.pkl and retrain with your current environment:\n"
        "```\npython -m src.model --synthetic\n```"
    )
    st.stop()

st.session_state.setdefault("alert_log", [])

tab_score, tab_queue, tab_model = st.tabs(
    ["Score a transaction", "Alert queue", "Model performance"])


# --------------------------------------------------------------------------- #
# Tab 1 - single transaction
# --------------------------------------------------------------------------- #
PRESETS = {
    "Normal purchase": dict(amount=2400.0, hour=14, location="Pune", new_device=False,
                            new_location=False, velocity=1, gap=7200),
    "Suspicious - elevated amount only (PDR demo B)": dict(
        amount=12000.0, hour=15, location="Pune", new_device=False,
        new_location=False, velocity=1, gap=5000),
    "Travelling customer (unusual but legitimate)": dict(
        amount=80000.0, hour=16, location="Delhi", new_device=False,
        new_location=True, velocity=1, gap=21600),
    "Account takeover (PDR demo)": dict(amount=85000.0, hour=2, location="Delhi",
                                        new_device=True, new_location=True,
                                        velocity=7, gap=45),
}

with tab_score:
    left, right = st.columns([1, 1.25], gap="large")

    with left:
        st.subheader("Simulated transaction")
        preset_name = st.selectbox("Demo scenario", list(PRESETS), index=2)
        p = PRESETS[preset_name]

        profile_ids = ["(new / unknown customer)"] + list(engine.profiles)[:50]
        chosen = st.selectbox("Customer profile", profile_ids)
        user_id = None if chosen.startswith("(") else chosen
        profile = engine.get_profile(user_id)

        amount = st.number_input("Amount (Rs)", min_value=1.0, value=float(p["amount"]), step=500.0)
        hour = st.slider("Hour of day", 0, 23, p["hour"])
        location = st.selectbox("Location", CITIES,
                                index=CITIES.index(p["location"]) if p["location"] in CITIES else 0)
        device = st.selectbox("Device", DEVICES + ["unknown-device"],
                              index=len(DEVICES) if p["new_device"] else 0)
        new_device = st.checkbox("Device not seen before for this customer", p["new_device"])
        new_location = st.checkbox("Location outside customer's usual area", p["new_location"])
        velocity = st.slider("Transactions in the last 10 minutes", 1, 12, p["velocity"])
        gap = st.number_input("Seconds since previous transaction", 0, 604800, p["gap"], step=30)

        if profile["txn_count"] == 0:
            st.caption("No transaction history for this customer. Using a default assumed "
                       f"baseline (Rs {profile['mean_amount']:,.0f}) for comparison only - "
                       "not a learned pattern.")
        else:
            st.caption(f"Profile baseline: avg Rs {profile['mean_amount']:,.0f} "
                       f"over {profile['txn_count']} past transactions.")

    error = validate_transaction(amount, hour, velocity, gap)
    if error:
        st.warning(error)
        st.stop()

    txn = {
        "amount": amount, "hour": hour, "location": location, "device_id": device,
        "txn_count_10min": velocity, "seconds_since_prev": gap,
        "is_new_device": int(new_device), "is_new_location": int(new_location),
    }
    try:
        result = engine.score(txn, user_id=user_id, profile=profile)
    except Exception as e:
        st.error(f"Could not score this transaction: {type(e).__name__}: {e}")
        st.stop()
    color = LEVEL_COLORS[result["level"]]

    with right:
        st.subheader("Risk assessment")
        st.markdown(f"""
        <div class="fs-card">
          <span class="fs-score" style="color:{color}">{result['score']}</span>
          <span style="color:#6b7280;font-size:1.1rem">/100</span>
          &nbsp;&nbsp;<span class="fs-level" style="background:{color}">{result['level']} RISK</span>
          <div class="fs-bar"><div class="fs-fill"
               style="width:{result['score']}%;background:{color}"></div></div>
          <div style="color:#6b7280;font-size:.85rem">
            model component {result['ml_points']} &nbsp;+&nbsp;
            behavioural rules {result['rule_points']}
          </div>
          <p style="margin-top:.9rem;margin-bottom:0"><b>Recommended action:</b> {result['action']}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Why this score")
        for r in result["reasons"]:
            st.markdown(
                f'<div class="fs-reason" style="border-left-color:{color}">'
                f'<span class="fs-pts">+{r["points"]}</span>'
                f'<b>{r["signal"]}</b><br>'
                f'<span style="color:#4b5563;font-size:.9rem">{r["detail"]}</span></div>',
                unsafe_allow_html=True)

        with st.expander("Feature vector sent to the model"):
            st.dataframe(pd.DataFrame([result["features"]]).T.rename(columns={0: "value"}))

        if result["level"] != "LOW":
            if st.button("Add this transaction to Alert Queue", type="primary"):
                top_reasons = "; ".join(
                    r["signal"] for r in result["reasons"][1:3] if r["points"] > 0
                ) or "-"
                st.session_state.alert_log.append({
                    "transaction_id": f"TXN-{len(st.session_state.alert_log) + 1:05d}",
                    "source": "Live (Score a transaction)",
                    "amount": txn["amount"],
                    "location": txn["location"],
                    "score": result["score"],
                    "level": result["level"],
                    "main_reason": top_reasons,
                    "action": result["action"],
                })
                st.success("Added to the Alert Queue - see the 'Alert queue' tab.")

    st.info("A suspicious transaction is not automatically fraudulent. Scores and thresholds "
            "are prototype demonstration values and support verification, not automatic blocking.")


# --------------------------------------------------------------------------- #
# Tab 2 - alert queue
# --------------------------------------------------------------------------- #
@st.cache_data
def simulate_batch(n: int = 40, seed: int = 7) -> pd.DataFrame:
    import numpy as np
    rng = np.random.default_rng(seed)
    users = list(engine.profiles)[:n] or [None] * n
    txns, uids = [], []
    for i in range(n):
        uid = users[i % len(users)]
        prof = engine.get_profile(uid)
        odd = rng.random() < 0.3
        txns.append({
            "amount": round(prof["mean_amount"] * (rng.uniform(3, 14) if odd
                                                   else rng.uniform(0.4, 2.0)), 2),
            "hour": int(rng.integers(0, 5) if odd else rng.integers(8, 22)),
            "location": CITIES[rng.integers(len(CITIES))],
            "device_id": "unknown-device" if odd and rng.random() < .6 else DEVICES[0],
            "txn_count_10min": int(rng.integers(3, 9) if odd else 1),
            "seconds_since_prev": int(rng.integers(20, 300) if odd else rng.integers(3600, 90000)),
            "is_new_device": int(odd and rng.random() < .6),
            "is_new_location": int(odd and rng.random() < .7),
        })
        uids.append(uid)
    return engine.score_batch(txns, uids)


with tab_queue:
    st.subheader("Prioritised alert queue")
    st.caption("Transactions you've scored and explicitly flagged (Live), merged with a "
               "simulated incoming batch (Simulated) - sorted so analysts see the riskiest "
               "cases first. Nothing here is a confirmed-fraud claim; each row still needs "
               "analyst verification.")

    sim = simulate_batch().reset_index(drop=True)
    sim = sim.rename(columns={"top_reason": "main_reason"})
    sim.insert(0, "transaction_id", [f"SIM-{i+1:05d}" for i in range(len(sim))])
    sim.insert(1, "source", "Simulated batch")
    sim = sim[["transaction_id", "source", "amount", "location", "score", "level",
              "main_reason", "action"]]

    live = pd.DataFrame(st.session_state.alert_log)
    batch = pd.concat([live, sim], ignore_index=True) if len(live) else sim
    batch = batch.sort_values("score", ascending=False).reset_index(drop=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("HIGH risk", int((batch.level == "HIGH").sum()))
    c2.metric("MEDIUM risk", int((batch.level == "MEDIUM").sum()))
    c3.metric("LOW risk", int((batch.level == "LOW").sum()))

    level_filter = st.multiselect("Show levels", ["HIGH", "MEDIUM", "LOW"],
                                  default=["HIGH", "MEDIUM"])
    source_filter = st.multiselect("Show source", ["Live (Score a transaction)", "Simulated batch"],
                                   default=["Live (Score a transaction)", "Simulated batch"])
    view = batch[batch.level.isin(level_filter) & batch.source.isin(source_filter)]
    st.dataframe(view, hide_index=True)

    if len(live):
        if st.button("Clear live alerts"):
            st.session_state.alert_log = []
            st.rerun()


# --------------------------------------------------------------------------- #
# Tab 3 - model performance
# --------------------------------------------------------------------------- #
with tab_model:
    st.subheader("Model performance on the held-out (future) period")
    meta = engine.metadata
    if meta:
        st.caption(f"Currently loaded model: trained on **{meta.get('source', 'unknown')}** "
                   f"data, {meta.get('n_train', 0):,} training transactions, decision "
                   f"threshold {meta.get('threshold', '-')}. This is the model actually "
                   f"powering the scores in this session.")
    m = get_metrics()
    if not m:
        st.warning("Run `python -m src.model` to generate models/metrics.json.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Precision", f"{m['precision']:.3f}")
        c2.metric("Recall", f"{m['recall']:.3f}")
        c3.metric("F1-score", f"{m['f1']:.3f}")
        c4.metric("PR-AUC", f"{m['pr_auc']:.3f}")
        st.caption(f"ROC-AUC {m['roc_auc']:.3f} | decision threshold {m['threshold']} "
                   f"| {m['n_test']:,} test transactions, {m['fraud_rate_test']:.2%} fraud. "
                   "Accuracy is deliberately not reported: on imbalanced fraud data it is "
                   "misleading.")

        cm = m["confusion_matrix"]
        st.markdown("#### Confusion matrix")
        st.dataframe(pd.DataFrame(cm,
                                  index=["actual legitimate", "actual fraud"],
                                  columns=["predicted legitimate", "predicted fraud"]))

        if m.get("feature_importance"):
            st.markdown("#### Which signals the model relies on")
            imp = pd.Series(m["feature_importance"]).sort_values(ascending=True)
            st.bar_chart(imp, horizontal=True)
