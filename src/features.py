"""
Step 2: CANONICAL EVENTS  ->  BEHAVIOURAL FEATURES (+ customer profiles).

Every feature answers the question "how does this transaction compare with what
this customer normally does?".  All of them are built in a single chronological
pass using only information available BEFORE the transaction, so there is no
leakage from the future into the training set.

The same feature definitions are reused at scoring time in
`features_from_transaction`, which is what keeps training and inference
consistent.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "log_amount",
    "amount_ratio",        # amount / customer's historical mean
    "amount_zscore",       # how many sd above their own mean
    "hour",
    "is_night",            # 00:00 - 05:59
    "seconds_since_prev",
    "txn_count_10min",     # velocity
    "txn_count_1h",
    "is_new_device",
    "is_new_location",
    "user_txn_index",      # how much history we have on this customer
]

PROFILES_PATH = os.path.join("models", "profiles.json")
FEATURES_PATH = os.path.join("data", "processed", "features.csv")

NIGHT_HOURS = set(range(0, 6))


# --------------------------------------------------------------------------- #
# Training-time feature building
# --------------------------------------------------------------------------- #
def build_features(events: pd.DataFrame, save: bool = True):
    """Return (X, y, profiles) built from the canonical event table."""
    events = events.sort_values("timestamp").reset_index(drop=True)

    state: dict[str, dict] = {}
    rows = []

    users = events["user_id"].to_numpy()
    times = events["timestamp"].to_numpy()
    amounts = events["amount"].to_numpy(dtype=float)
    devices = events["device_id"].to_numpy()
    locations = events["location"].to_numpy()

    for i in range(len(events)):
        uid = users[i]
        ts = int(times[i])
        amt = float(amounts[i])
        dev = devices[i]
        loc = locations[i]

        s = state.get(uid)
        if s is None:
            s = {"n": 0, "sum": 0.0, "sumsq": 0.0, "devices": set(),
                 "locations": set(), "last_ts": None, "recent": []}
            state[uid] = s

        # ---- profile BEFORE this transaction -----------------------------
        n = s["n"]
        mean = s["sum"] / n if n else amt           # first txn: no deviation
        var = max(s["sumsq"] / n - mean ** 2, 0.0) if n else 0.0
        std = float(np.sqrt(var))

        recent = [t for t in s["recent"] if ts - t <= 3600]
        rows.append({
            "log_amount": float(np.log1p(amt)),
            "amount_ratio": amt / (mean + 1.0),
            "amount_zscore": (amt - mean) / (std + 1.0),
            "hour": (ts // 3600) % 24,
            "is_night": int(((ts // 3600) % 24) in NIGHT_HOURS),
            "seconds_since_prev": float(ts - s["last_ts"]) if s["last_ts"] is not None else 86400.0,
            "txn_count_10min": sum(1 for t in recent if ts - t <= 600) + 1,
            "txn_count_1h": len(recent) + 1,
            "is_new_device": int(n > 0 and dev not in s["devices"]),
            "is_new_location": int(n > 0 and loc not in s["locations"]),
            "user_txn_index": n,
        })

        # ---- profile updated WITH this transaction -----------------------
        s["n"] = n + 1
        s["sum"] += amt
        s["sumsq"] += amt ** 2
        s["devices"].add(dev)
        s["locations"].add(loc)
        s["last_ts"] = ts
        recent.append(ts)
        s["recent"] = recent[-50:]

    X = pd.DataFrame(rows)[FEATURE_COLUMNS]
    y = events["is_fraud"].astype(int).reset_index(drop=True)
    profiles = _finalise_profiles(state)

    if save:
        os.makedirs(os.path.dirname(FEATURES_PATH), exist_ok=True)
        pd.concat([events[["user_id", "timestamp"]], X, y], axis=1).to_csv(FEATURES_PATH, index=False)
        save_profiles(profiles)
        print(f"[features] built {X.shape[0]:,} x {X.shape[1]} feature matrix")
    return X, y, profiles


def _finalise_profiles(state: dict, max_users: int = 500) -> dict:
    """Convert the streaming state into a JSON-serialisable profile store.

    Only the busiest customers are kept so models/profiles.json stays small -
    the dashboard just needs a handful of realistic demo customers.
    """
    items = sorted(state.items(), key=lambda kv: kv[1]["n"], reverse=True)[:max_users]
    profiles = {}
    for uid, s in items:
        n = s["n"]
        mean = s["sum"] / n
        var = max(s["sumsq"] / n - mean ** 2, 0.0)
        profiles[uid] = {
            "txn_count": n,
            "mean_amount": round(mean, 2),
            "std_amount": round(float(np.sqrt(var)), 2),
            "known_devices": sorted(s["devices"])[:10],
            "known_locations": sorted(s["locations"])[:10],
        }
    return profiles


def save_profiles(profiles: dict, path: str = PROFILES_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(profiles, fh, indent=2)


def load_profiles(path: str = PROFILES_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        return json.load(fh)


def default_profile() -> dict:
    """Fallback profile used when a customer is unknown (cold start)."""
    return {
        "txn_count": 0,
        "mean_amount": 2500.0,
        "std_amount": 1500.0,
        "known_devices": [],
        "known_locations": [],
    }


# --------------------------------------------------------------------------- #
# Scoring-time feature building  (one live / simulated transaction)
# --------------------------------------------------------------------------- #
def features_from_transaction(txn: dict, profile: dict | None = None) -> pd.DataFrame:
    """Build a single-row feature frame using exactly the training definitions.

    txn keys
    --------
    amount            float, required
    hour              int 0-23, required
    device_id         str    (compared against profile["known_devices"])
    location          str    (compared against profile["known_locations"])
    txn_count_10min   int, default 1  - transactions in the last 10 minutes
    seconds_since_prev float, default 86400
    """
    p = {**default_profile(), **(profile or {})}
    amt = float(txn["amount"])
    mean = float(p["mean_amount"])
    std = float(p["std_amount"])
    hour = int(txn.get("hour", 12))
    v10 = int(txn.get("txn_count_10min", 1))

    row = {
        "log_amount": float(np.log1p(amt)),
        "amount_ratio": amt / (mean + 1.0),
        "amount_zscore": (amt - mean) / (std + 1.0),
        "hour": hour,
        "is_night": int(hour in NIGHT_HOURS),
        "seconds_since_prev": float(txn.get("seconds_since_prev", 86400.0)),
        "txn_count_10min": v10,
        "txn_count_1h": int(txn.get("txn_count_1h", max(v10, 1))),
        "is_new_device": int(
            txn.get("is_new_device",
                    bool(p["known_devices"]) and txn.get("device_id") not in p["known_devices"])
        ),
        "is_new_location": int(
            txn.get("is_new_location",
                    bool(p["known_locations"]) and txn.get("location") not in p["known_locations"])
        ),
        "user_txn_index": int(p["txn_count"]),
    }
    return pd.DataFrame([row])[FEATURE_COLUMNS]
