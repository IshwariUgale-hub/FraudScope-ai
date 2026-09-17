"""
Step 1 of the pipeline: RAW DATA  ->  CANONICAL EVENT TABLE.

Everything downstream (features, model, risk engine, dashboard) only ever sees
the canonical schema below, so the project works with either:

  * the real Kaggle IEEE-CIS file  data/raw/train_transaction.csv
    (optionally merged with train_identity.csv), or
  * a built-in synthetic generator, so you can demo without any download.

Canonical schema
----------------
user_id    : str   identifier of the customer / card
timestamp  : int   seconds since an arbitrary epoch (must be sortable)
amount     : float transaction amount
device_id  : str   device / channel fingerprint
location   : str   city or billing region
is_fraud   : int   0 / 1 label
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

CANONICAL_COLUMNS = ["user_id", "timestamp", "amount", "device_id", "location", "is_fraud"]

RAW_PATH = os.path.join("data", "raw", "train_transaction.csv")
IDENTITY_PATH = os.path.join("data", "raw", "train_identity.csv")
EVENTS_PATH = os.path.join("data", "processed", "events.csv")


# --------------------------------------------------------------------------- #
# Real dataset
# --------------------------------------------------------------------------- #
def load_raw(path: str = RAW_PATH, identity_path: str = IDENTITY_PATH, nrows=None):
    """Read the IEEE-CIS transaction file if it exists, else return None."""
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, nrows=nrows, low_memory=False)
    if os.path.exists(identity_path):
        ident = pd.read_csv(identity_path, low_memory=False)
        df = df.merge(ident, on="TransactionID", how="left")
    return df


def adapt_ieee(df: pd.DataFrame) -> pd.DataFrame:
    """Map the IEEE-CIS columns onto the canonical schema.

    The competition data has no explicit customer id, so we use the standard
    community proxy: card1 + addr1 identifies a card/billing pair well enough
    for behavioural profiling.
    """
    out = pd.DataFrame()

    card = df.get("card1", pd.Series(0, index=df.index)).fillna(-1).astype(int).astype(str)
    addr = df.get("addr1", pd.Series(0, index=df.index)).fillna(-1).astype(int).astype(str)
    out["user_id"] = "C" + card + "_" + addr

    # TransactionDT is "seconds from a reference datetime" - exactly what we need.
    out["timestamp"] = df["TransactionDT"].astype("int64")
    out["amount"] = df["TransactionAmt"].astype(float)

    # Device: real fingerprint if train_identity.csv was merged, otherwise a
    # coarse channel proxy (product + card type). Documented as a limitation.
    if "DeviceInfo" in df.columns:
        device = df["DeviceInfo"].fillna("unknown_device").astype(str)
        if "id_31" in df.columns:
            device = device + "|" + df["id_31"].fillna("na").astype(str)
    else:
        device = (
            df.get("ProductCD", pd.Series("NA", index=df.index)).astype(str)
            + "|"
            + df.get("card6", pd.Series("NA", index=df.index)).fillna("NA").astype(str)
        )
    out["device_id"] = device

    # Location: billing region code, used as a stand-in for city.
    out["location"] = "R" + addr

    out["is_fraud"] = df["isFraud"].astype(int)
    return out[CANONICAL_COLUMNS]


# --------------------------------------------------------------------------- #
# Synthetic fallback  (so the prototype runs with zero downloads)
# --------------------------------------------------------------------------- #
CITIES = ["Pune", "Mumbai", "Delhi", "Bengaluru", "Nagpur", "Hyderabad", "Chennai", "Jaipur"]
DEVICES = ["android-a", "android-b", "ios-a", "ios-b", "web-chrome", "web-edge"]


def _daytime_profile():
    """Hour-of-day probability for normal behaviour (low at night)."""
    w = np.array([0.4, 0.3, 0.25, 0.25, 0.3, 0.5, 1.0, 1.6, 2.2, 2.6, 2.8, 2.9,
                  3.0, 2.8, 2.6, 2.5, 2.6, 2.8, 3.0, 2.9, 2.4, 1.8, 1.1, 0.6])
    return w / w.sum()


def generate_synthetic(n_users: int = 1200, txns_per_user: int = 40,
                       fraud_rate: float = 0.025, seed: int = 42) -> pd.DataFrame:
    """Simulate a behaviourally realistic transaction log.

    Fraud is made *correlated but not deterministic* with the risk signals:
    some frauds look ordinary and some legitimate transactions look strange,
    which is what forces the model to learn instead of memorising one rule.
    """
    rng = np.random.default_rng(seed)
    hour_p = _daytime_profile()
    rows = []

    for u in range(n_users):
        user_id = f"U{u:05d}"
        home = CITIES[rng.integers(len(CITIES))]
        home_device = DEVICES[rng.integers(len(DEVICES))]
        mean_amt = float(np.exp(rng.normal(7.4, 0.7)))         # ~ Rs 1.6k median
        t = int(rng.integers(0, 86400 * 30))                   # first txn time

        n = int(max(8, rng.normal(txns_per_user, 10)))
        for _ in range(n):
            t += int(rng.exponential(60 * 60 * 20))            # gap to next txn
            is_fraud = int(rng.random() < fraud_rate)

            if is_fraud:
                # Fraud raises several signals at once, but each only with some
                # probability, so the two classes genuinely overlap and the
                # model cannot separate them with a single hand-written rule.
                amount = mean_amt * float(rng.uniform(0.7, 9.0))
                if rng.random() < 0.40:                        # "quiet" fraud
                    hour = int(rng.choice(24, p=hour_p))
                else:
                    hour = int(rng.choice([0, 1, 2, 3, 4, 23], p=[.2, .2, .2, .15, .15, .1]))
                location = home if rng.random() < 0.55 else CITIES[rng.integers(len(CITIES))]
                device = home_device if rng.random() < 0.50 else f"unk-{rng.integers(9999)}"
                burst = int(rng.choice([1, 1, 1, 1, 2, 3]))
            else:
                amount = mean_amt * float(np.exp(rng.normal(0, 0.8)))
                if rng.random() < 0.06:                        # legitimate but odd
                    amount *= float(rng.uniform(3, 10))
                hour = int(rng.choice(24, p=hour_p)) if rng.random() < 0.93 \
                    else int(rng.integers(0, 6))
                location = home if rng.random() < 0.82 else CITIES[rng.integers(len(CITIES))]
                device = home_device if rng.random() < 0.85 else DEVICES[rng.integers(len(DEVICES))]
                burst = 1 if rng.random() < 0.94 else int(rng.choice([2, 3]))

            day = t // 86400
            base = day * 86400 + hour * 3600 + int(rng.integers(0, 3600))
            for b in range(burst):
                rows.append({
                    "user_id": user_id,
                    "timestamp": base + b * int(rng.integers(20, 200)),
                    "amount": round(amount * (1 if b == 0 else float(rng.uniform(0.3, 1.2))), 2),
                    "device_id": device,
                    "location": location,
                    "is_fraud": is_fraud if b == 0 else int(is_fraud and rng.random() < 0.6),
                })
            t = base

    df = pd.DataFrame(rows)
    return df.sort_values("timestamp").reset_index(drop=True)[CANONICAL_COLUMNS]


# --------------------------------------------------------------------------- #
# Entry point used by model.py and the notebooks
# --------------------------------------------------------------------------- #
def clean(events: pd.DataFrame) -> pd.DataFrame:
    """Drop impossible rows, fill gaps, enforce chronological order."""
    events = events.dropna(subset=["user_id", "timestamp", "amount"])
    events = events[events["amount"] > 0].copy()
    events["device_id"] = events["device_id"].fillna("unknown_device").astype(str)
    events["location"] = events["location"].fillna("unknown_location").astype(str)
    events["is_fraud"] = events["is_fraud"].astype(int)
    return events.sort_values("timestamp").reset_index(drop=True)


def build_events(use_synthetic: bool = False, nrows=None, save: bool = True) -> pd.DataFrame:
    """Return the canonical event table, from the real CSV when available."""
    events = None
    if not use_synthetic:
        raw = load_raw(nrows=nrows)
        if raw is not None:
            print(f"[preprocessing] loaded real dataset: {raw.shape[0]:,} rows")
            events = adapt_ieee(raw)

    if events is None:
        print("[preprocessing] no raw CSV found -> generating synthetic data")
        events = generate_synthetic()

    events = clean(events)
    if save:
        os.makedirs(os.path.dirname(EVENTS_PATH), exist_ok=True)
        events.to_csv(EVENTS_PATH, index=False)
        print(f"[preprocessing] wrote {EVENTS_PATH} ({len(events):,} rows, "
              f"fraud rate {events.is_fraud.mean():.3%})")
    return events


if __name__ == "__main__":
    build_events()
