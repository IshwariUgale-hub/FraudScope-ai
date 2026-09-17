"""
Step 5: the object the dashboard (or a future API) actually talks to.

    from src.predictor import FraudScope
    fs = FraudScope.load()
    result = fs.score({"amount": 85000, "hour": 2, "location": "Delhi",
                       "device_id": "unknown-device", "txn_count_10min": 7},
                      user_id="U00042")
    print(result["score"], result["level"], result["reasons"])
"""
from __future__ import annotations

import os

import joblib
import pandas as pd

from .features import (FEATURE_COLUMNS, default_profile, features_from_transaction,
                       load_profiles)
from .risk_engine import explain_text, score_risk

MODEL_PATH = os.path.join("models", "fraud_model.pkl")


class FraudScope:
    """Loads the trained artefacts once and scores transactions on demand."""

    def __init__(self, model, feature_columns, metadata, profiles):
        self.model = model
        self.feature_columns = feature_columns
        self.metadata = metadata or {}
        self.profiles = profiles or {}

    # ------------------------------------------------------------------ #
    @classmethod
    def load(cls, model_path: str = MODEL_PATH):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"{model_path} not found. Train the model first:  python -m src.model"
            )
        bundle = joblib.load(model_path)
        return cls(bundle["model"],
                   bundle.get("feature_columns", FEATURE_COLUMNS),
                   bundle.get("metadata", {}),
                   load_profiles())

    # ------------------------------------------------------------------ #
    def get_profile(self, user_id: str | None):
        if user_id and user_id in self.profiles:
            return self.profiles[user_id]
        return default_profile()

    def predict_proba(self, X: pd.DataFrame) -> float:
        X = X[self.feature_columns]
        return float(self.model.predict_proba(X)[0][1])

    def score(self, txn: dict, user_id: str | None = None, profile: dict | None = None) -> dict:
        """Score one simulated / live transaction and explain the result."""
        profile = profile or self.get_profile(user_id)
        X = features_from_transaction(txn, profile)
        prob = self.predict_proba(X)

        feats = X.iloc[0].to_dict()
        feats["amount"] = float(txn["amount"])
        result = score_risk(prob, feats, txn)

        out = result.as_dict()
        out["user_id"] = user_id
        out["features"] = feats
        out["summary"] = explain_text(result)
        return out

    def score_batch(self, transactions: list, user_ids: list | None = None) -> pd.DataFrame:
        """Convenience helper for the dashboard's alert queue."""
        user_ids = user_ids or [None] * len(transactions)
        rows = []
        for txn, uid in zip(transactions, user_ids):
            r = self.score(txn, user_id=uid)
            rows.append({
                "user_id": uid,
                "amount": txn["amount"],
                "hour": txn.get("hour"),
                "location": txn.get("location"),
                "score": r["score"],
                "level": r["level"],
                "top_reason": r["reasons"][1]["signal"] if len(r["reasons"]) > 1 else "-",
                "action": r["action"],
            })
        return pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    fs = FraudScope.load()
    demo = {"amount": 85000, "hour": 2, "location": "Delhi", "device_id": "unknown-device",
            "txn_count_10min": 7, "seconds_since_prev": 45,
            "is_new_device": 1, "is_new_location": 1}
    res = fs.score(demo)
    print(res["summary"])
    for r in res["reasons"]:
        print(f"  +{r['points']:>5}  {r['signal']}: {r['detail']}")
