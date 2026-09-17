"""
Step 3: TRAIN, EVALUATE, SAVE.

Run from the project root:

    python -m src.model                # uses data/raw/train_transaction.csv if present
    python -m src.model --synthetic    # force the built-in simulator
    python -m src.model --nrows 100000 # train on a slice of the real file (fast)

Because fraud data is heavily imbalanced, the model is evaluated with
precision / recall / F1 / PR-AUC / confusion matrix, never accuracy alone, and
the decision threshold is chosen from the precision-recall curve instead of
being left at 0.5.
"""
from __future__ import annotations

import argparse
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (average_precision_score, classification_report,
                             confusion_matrix, precision_recall_curve, roc_auc_score)

from .features import FEATURE_COLUMNS, build_features
from .preprocessing import build_events

MODEL_PATH = os.path.join("models", "fraud_model.pkl")
METRICS_PATH = os.path.join("models", "metrics.json")


def time_split(X: pd.DataFrame, y: pd.Series, test_size: float = 0.2):
    """Chronological split: train on the past, test on the future.

    A random split would let the model see later transactions of the same
    customer it is being tested on, which inflates every metric.
    """
    cut = int(len(X) * (1 - test_size))
    return X.iloc[:cut], X.iloc[cut:], y.iloc[:cut], y.iloc[cut:]


def build_model(pos_weight: float) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_iter=300,
        learning_rate=0.06,
        max_depth=6,
        min_samples_leaf=40,
        l2_regularization=1.0,
        early_stopping=True,
        validation_fraction=0.1,
        random_state=42,
        class_weight={0: 1.0, 1: pos_weight},
    )


def evaluate(model, X_test, y_test) -> dict:
    proba = model.predict_proba(X_test)[:, 1]

    precision, recall, thresholds = precision_recall_curve(y_test, proba)
    f1 = 2 * precision * recall / np.clip(precision + recall, 1e-9, None)
    best = int(np.nanargmax(f1[:-1])) if len(thresholds) else 0
    threshold = float(thresholds[best]) if len(thresholds) else 0.5

    pred = (proba >= threshold).astype(int)
    cm = confusion_matrix(y_test, pred).tolist()
    report = classification_report(y_test, pred, output_dict=True, zero_division=0)

    metrics = {
        "n_test": int(len(y_test)),
        "fraud_rate_test": float(y_test.mean()),
        "threshold": round(threshold, 4),
        "precision": round(report["1"]["precision"], 4),
        "recall": round(report["1"]["recall"], 4),
        "f1": round(report["1"]["f1-score"], 4),
        "pr_auc": round(float(average_precision_score(y_test, proba)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
        "confusion_matrix": cm,
    }
    return metrics


def permutation_importance_fast(model, X_test, y_test, n_repeats: int = 3) -> dict:
    """Cheap permutation importance on PR-AUC - used by the dashboard."""
    base = average_precision_score(y_test, model.predict_proba(X_test)[:, 1])
    rng = np.random.default_rng(0)
    out = {}
    for col in X_test.columns:
        drops = []
        for _ in range(n_repeats):
            Xp = X_test.copy()
            Xp[col] = rng.permutation(Xp[col].to_numpy())
            drops.append(base - average_precision_score(y_test, model.predict_proba(Xp)[:, 1]))
        out[col] = round(float(np.mean(drops)), 5)
    return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))


def train(use_synthetic: bool = False, nrows=None, importance: bool = True):
    events = build_events(use_synthetic=use_synthetic, nrows=nrows)
    X, y, _profiles = build_features(events)

    X_train, X_test, y_train, y_test = time_split(X, y)
    pos = max(int(y_train.sum()), 1)
    pos_weight = float(len(y_train) - pos) / pos
    print(f"[model] train={len(X_train):,}  test={len(X_test):,}  "
          f"fraud in train={y_train.mean():.3%}  pos_weight={pos_weight:.1f}")

    model = build_model(pos_weight)
    model.fit(X_train, y_train)

    metrics = evaluate(model, X_test, y_test)
    if importance:
        metrics["feature_importance"] = permutation_importance_fast(
            model, X_test.sample(min(len(X_test), 20000), random_state=0),
            y_test.loc[X_test.sample(min(len(X_test), 20000), random_state=0).index])

    print(json.dumps({k: v for k, v in metrics.items() if k != "feature_importance"}, indent=2))

    os.makedirs("models", exist_ok=True)
    joblib.dump({
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "metadata": {
            "source": "synthetic" if use_synthetic else "auto",
            "n_train": int(len(X_train)),
            "threshold": metrics["threshold"],
            "metrics": {k: metrics[k] for k in
                        ("precision", "recall", "f1", "pr_auc", "roc_auc")},
        },
    }, MODEL_PATH)
    with open(METRICS_PATH, "w") as fh:
        json.dump(metrics, fh, indent=2)
    print(f"[model] saved {MODEL_PATH} and {METRICS_PATH}")
    return model, metrics


def load_metrics(path: str = METRICS_PATH) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path) as fh:
        return json.load(fh)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Train the FRAUDSCOPE AI model")
    ap.add_argument("--synthetic", action="store_true", help="force the built-in simulator")
    ap.add_argument("--nrows", type=int, default=None, help="limit rows read from the real CSV")
    ap.add_argument("--no-importance", action="store_true")
    args = ap.parse_args()
    train(use_synthetic=args.synthetic, nrows=args.nrows, importance=not args.no_importance)
