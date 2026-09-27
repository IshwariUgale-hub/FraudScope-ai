from __future__ import annotations

import logging
import time
import uuid
from typing import List, Optional, Tuple

import numpy as np
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.transaction import Transaction
from app.schemas.transaction import (
    ReasonItem,
    TransactionDetailResponse,
    TransactionScoreRequest,
    TransactionScoreResponse,
)
from src.features import default_profile, load_profiles
from src.predictor import FraudScope

logger = logging.getLogger("fraudscope.service")


class FraudService:
    """Service wrapper managing the FraudScope ML inference engine and PostgreSQL persistence.

    Loads the trained HistGradientBoostingClassifier and profiles once
    at startup, derives behavioral history from the database, evaluates transactions,
    and persists assessment results.
    """

    def __init__(self) -> None:
        self.engine: Optional[FraudScope] = None
        self._is_ready: bool = False
        self._load_error: Optional[str] = None

    @property
    def is_ready(self) -> bool:
        """Returns True if the ML model is loaded and ready for scoring."""
        return self._is_ready and self.engine is not None

    def initialize(self) -> None:
        """Loads FraudScope engine once using configured artifact paths."""
        try:
            logger.info("Initializing FraudScope ML engine from %s...", settings.MODEL_PATH)
            self.engine = FraudScope.load(settings.MODEL_PATH)

            # Ensure customer profiles are loaded from the absolute profiles path
            if hasattr(self.engine, "profiles") and not self.engine.profiles:
                self.engine.profiles = load_profiles(settings.PROFILES_PATH)

            self._is_ready = True
            self._load_error = None
            logger.info(
                "FraudScope ML engine initialized successfully (profiles loaded: %d)",
                len(self.engine.profiles) if self.engine.profiles else 0,
            )
        except Exception as exc:
            self._is_ready = False
            self._load_error = str(exc)
            logger.error("Failed to load FraudScope ML engine: %s", exc, exc_info=True)
            raise RuntimeError(f"ML Model initialization failed: {exc}") from exc

    def calculate_behavioral_context(
        self,
        request: TransactionScoreRequest,
        current_ts: int,
        past_txns: List[Transaction],
    ) -> Tuple[int, int, float, Optional[int], Optional[int], dict]:
        """Derives transaction velocity, time delta, device novelty, and user baseline from DB history.

        Returns:
            (txn_count_10min, txn_count_1h, seconds_since_prev, is_new_device, is_new_location, profile)
        """
        user_id = request.user_id

        if past_txns:
            # Case A: Real transaction history exists in the database
            prev_txn = past_txns[0]
            derived_seconds_since_prev = max(0.0, float(current_ts - prev_txn.timestamp))

            # 10-minute window velocity (600 seconds)
            cutoff_10m = current_ts - 600
            txns_in_10m = sum(1 for t in past_txns if t.timestamp >= cutoff_10m)
            derived_txn_count_10min = txns_in_10m + 1

            # 1-hour window velocity (3600 seconds)
            cutoff_1h = current_ts - 3600
            txns_in_1h = sum(1 for t in past_txns if t.timestamp >= cutoff_1h)
            derived_txn_count_1h = txns_in_1h + 1

            # Device and location novelty derived from stored user history
            known_devices = {t.device_id for t in past_txns}
            derived_is_new_device = 1 if request.device_id not in known_devices else 0

            known_locations = {t.location for t in past_txns}
            derived_is_new_location = 1 if request.location not in known_locations else 0

            # Dynamic customer profile from DB if not already present in static profiles
            if user_id and user_id in self.engine.profiles:
                profile = self.engine.profiles[user_id]
            else:
                amounts = [t.amount for t in past_txns]
                profile = {
                    "txn_count": len(past_txns),
                    "mean_amount": float(np.mean(amounts)),
                    "std_amount": float(np.std(amounts)) if len(amounts) > 1 else 1500.0,
                    "known_devices": list(known_devices)[:10],
                    "known_locations": list(known_locations)[:10],
                }

            return (
                derived_txn_count_10min,
                derived_txn_count_1h,
                derived_seconds_since_prev,
                derived_is_new_device,
                derived_is_new_location,
                profile,
            )

        # Case B: Cold-start or zero database history
        # Preserve backward-compatibility for demo requests while safely handling cold-start
        txn_count_10min = request.txn_count_10min if request.txn_count_10min is not None else 1
        txn_count_1h = request.txn_count_1h if request.txn_count_1h is not None else txn_count_10min
        seconds_since_prev = (
            request.seconds_since_prev if request.seconds_since_prev is not None else 86400.0
        )
        is_new_device = request.is_new_device
        is_new_location = request.is_new_location

        # Use profile from model store if available (e.g., demo profiles), else default cold-start profile
        profile = self.engine.get_profile(user_id) if self.engine else default_profile()

        return (
            txn_count_10min,
            txn_count_1h,
            seconds_since_prev,
            is_new_device,
            is_new_location,
            profile,
        )

    def score_transaction(
        self,
        request: TransactionScoreRequest,
        db: Session,
    ) -> TransactionScoreResponse:
        """Evaluates transaction risk using DB behavioral context and existing FraudScope ML Engine.

        Persists the transaction and scoring outcome to PostgreSQL.
        """
        if not self.is_ready or self.engine is None:
            logger.error("Attempted transaction scoring while ML engine is unavailable: %s", self._load_error)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Fraud detection engine is unavailable. Please check system health.",
            )

        current_ts = request.timestamp if request.timestamp is not None else int(time.time())
        user_id = request.user_id

        # Query past transactions for this user from PostgreSQL
        past_txns: List[Transaction] = []
        if user_id:
            try:
                past_txns = (
                    db.query(Transaction)
                    .filter(Transaction.user_id == user_id)
                    .order_by(Transaction.timestamp.desc())
                    .all()
                )
            except Exception as exc:
                logger.error("Database query error for user %s: %s", user_id, exc)
                # Allow fallback without crashing if DB encounters an issue

        # Calculate backend-derived behavioral context
        (
            v10,
            v1h,
            sec_prev,
            is_new_dev,
            is_new_loc,
            profile,
        ) = self.calculate_behavioral_context(request, current_ts, past_txns)

        # Build feature transaction dictionary for existing FraudScope engine
        txn_dict = {
            "amount": request.amount,
            "hour": request.hour,
            "device_id": request.device_id,
            "location": request.location,
            "txn_count_10min": v10,
            "seconds_since_prev": sec_prev,
            "txn_count_1h": v1h,
        }

        if is_new_dev is not None:
            txn_dict["is_new_device"] = is_new_dev
        if is_new_loc is not None:
            txn_dict["is_new_location"] = is_new_loc
        if request.currency is not None:
            txn_dict["currency"] = request.currency

        try:
            # Delegate directly to EXISTING FraudScope.score() in src/predictor.py
            result = self.engine.score(txn_dict, user_id=user_id, profile=profile)
        except Exception as exc:
            logger.error("Prediction failure for user %s: %s", user_id, exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to evaluate transaction risk due to an internal scoring error.",
            ) from exc

        # Generate unique transaction_id if not provided
        txn_id = request.transaction_id or f"TXN-{uuid.uuid4().hex[:8].upper()}"

        reasons_list = [
            ReasonItem(
                signal=r["signal"],
                detail=r["detail"],
                points=float(r["points"]),
            )
            for r in result.get("reasons", [])
        ]

        # Persist transaction + fraud assessment in PostgreSQL
        try:
            db_transaction = Transaction(
                transaction_id=txn_id,
                user_id=user_id or "unknown",
                amount=request.amount,
                timestamp=current_ts,
                device_id=request.device_id,
                location=request.location,
                currency=request.currency or "Rs",
                txn_count_10min=v10,
                txn_count_1h=v1h,
                seconds_since_prev=sec_prev,
                is_new_device=is_new_dev,
                is_new_location=is_new_loc,
                risk_score=result["score"],
                risk_level=result["level"],
                ml_probability=round(float(result["ml_probability"]), 4),
                ml_points=float(result["ml_points"]),
                rule_points=float(result["rule_points"]),
                recommended_action=result["action"],
                summary=result["summary"],
                reasons=[r.model_dump() for r in reasons_list],
                features=result.get("features", {}),
            )
            db.add(db_transaction)
            db.commit()
            db.refresh(db_transaction)
            logger.info("Persisted transaction %s for user %s to database (Score: %d)", txn_id, user_id, result["score"])
        except Exception as exc:
            db.rollback()
            logger.error("Failed to persist transaction %s to database: %s", txn_id, exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist transaction assessment to the database.",
            ) from exc

        return TransactionScoreResponse(
            transaction_id=txn_id,
            user_id=user_id,
            risk_score=result["score"],
            risk_level=result["level"],
            ml_probability=round(float(result["ml_probability"]), 4),
            ml_points=float(result["ml_points"]),
            rule_points=float(result["rule_points"]),
            reasons=reasons_list,
            summary=result["summary"],
            recommended_action=result["action"],
            features=result.get("features", {}),
        )

    def get_transaction_by_id(
        self,
        transaction_id: str,
        db: Session,
    ) -> TransactionDetailResponse:
        """Retrieves a stored transaction and its risk assessment by transaction_id."""
        txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
        if not txn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction with ID '{transaction_id}' was not found.",
            )

        raw_reasons = txn.reasons or []
        reasons_list = [
            ReasonItem(
                signal=r.get("signal", ""),
                detail=r.get("detail", ""),
                points=float(r.get("points", 0.0)),
            )
            for r in raw_reasons
        ]

        return TransactionDetailResponse(
            id=txn.id,
            transaction_id=txn.transaction_id,
            user_id=txn.user_id,
            amount=txn.amount,
            timestamp=txn.timestamp,
            device_id=txn.device_id,
            location=txn.location,
            currency=txn.currency,
            txn_count_10min=txn.txn_count_10min,
            txn_count_1h=txn.txn_count_1h,
            seconds_since_prev=txn.seconds_since_prev,
            is_new_device=txn.is_new_device,
            is_new_location=txn.is_new_location,
            risk_score=txn.risk_score,
            risk_level=txn.risk_level,
            ml_probability=txn.ml_probability,
            ml_points=txn.ml_points,
            rule_points=txn.rule_points,
            recommended_action=txn.recommended_action,
            summary=txn.summary,
            reasons=reasons_list,
            features=txn.features or {},
            created_at=txn.created_at,
        )

    def get_user_transactions(
        self,
        user_id: str,
        db: Session,
        limit: int = 20,
        skip: int = 0,
    ) -> Tuple[int, List[TransactionDetailResponse]]:
        """Retrieves recent transactions for a given user with pagination."""
        total = db.query(Transaction).filter(Transaction.user_id == user_id).count()
        txns = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        results = []
        for txn in txns:
            raw_reasons = txn.reasons or []
            reasons_list = [
                ReasonItem(
                    signal=r.get("signal", ""),
                    detail=r.get("detail", ""),
                    points=float(r.get("points", 0.0)),
                )
                for r in raw_reasons
            ]
            results.append(
                TransactionDetailResponse(
                    id=txn.id,
                    transaction_id=txn.transaction_id,
                    user_id=txn.user_id,
                    amount=txn.amount,
                    timestamp=txn.timestamp,
                    device_id=txn.device_id,
                    location=txn.location,
                    currency=txn.currency,
                    txn_count_10min=txn.txn_count_10min,
                    txn_count_1h=txn.txn_count_1h,
                    seconds_since_prev=txn.seconds_since_prev,
                    is_new_device=txn.is_new_device,
                    is_new_location=txn.is_new_location,
                    risk_score=txn.risk_score,
                    risk_level=txn.risk_level,
                    ml_probability=txn.ml_probability,
                    ml_points=txn.ml_points,
                    rule_points=txn.rule_points,
                    recommended_action=txn.recommended_action,
                    summary=txn.summary,
                    reasons=reasons_list,
                    features=txn.features or {},
                    created_at=txn.created_at,
                )
            )

        return total, results


# Global service singleton instance
fraud_service = FraudService()
