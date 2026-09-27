from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.transaction import ReasonItem, TransactionScoreRequest, TransactionScoreResponse
from src.features import load_profiles
from src.predictor import FraudScope

logger = logging.getLogger("fraudscope.service")


class FraudService:
    """Service wrapper managing the FraudScope ML inference engine.
    
    Loads the trained HistGradientBoostingClassifier and profiles once
    at startup and evaluates incoming transaction requests.
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

    def score_transaction(self, request: TransactionScoreRequest) -> TransactionScoreResponse:
        """Evaluates transaction risk using existing FraudScope ML + Risk Engine."""
        if not self.is_ready or self.engine is None:
            logger.error("Attempted transaction scoring while ML engine is unavailable: %s", self._load_error)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Fraud detection engine is unavailable. Please check system health.",
            )

        # Build transaction dictionary for the existing engine
        txn_dict = {
            "amount": request.amount,
            "hour": request.hour,
            "device_id": request.device_id,
            "location": request.location,
            "txn_count_10min": request.txn_count_10min,
            "seconds_since_prev": request.seconds_since_prev,
        }

        if request.is_new_device is not None:
            txn_dict["is_new_device"] = request.is_new_device
        if request.is_new_location is not None:
            txn_dict["is_new_location"] = request.is_new_location
        if request.txn_count_1h is not None:
            txn_dict["txn_count_1h"] = request.txn_count_1h
        if request.currency is not None:
            txn_dict["currency"] = request.currency

        try:
            # Delegate to EXISTING FraudScope.score() in src/predictor.py
            result = self.engine.score(txn_dict, user_id=request.user_id)
        except Exception as exc:
            logger.error("Prediction failure for user %s: %s", request.user_id, exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to evaluate transaction risk due to an internal scoring error.",
            ) from exc

        # Generate unique transaction_id if not provided by client
        txn_id = request.transaction_id or f"TXN-{uuid.uuid4().hex[:8].upper()}"

        return TransactionScoreResponse(
            transaction_id=txn_id,
            user_id=request.user_id,
            risk_score=result["score"],
            risk_level=result["level"],
            ml_probability=round(float(result["ml_probability"]), 4),
            ml_points=float(result["ml_points"]),
            rule_points=float(result["rule_points"]),
            reasons=[
                ReasonItem(
                    signal=r["signal"],
                    detail=r["detail"],
                    points=float(r["points"]),
                )
                for r in result.get("reasons", [])
            ],
            summary=result["summary"],
            recommended_action=result["action"],
            features=result.get("features", {}),
        )


# Global service instance
fraud_service = FraudService()
