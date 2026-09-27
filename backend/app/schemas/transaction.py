from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReasonItem(BaseModel):
    """An individual behavioural or statistical signal contributing to the risk score."""

    signal: str = Field(..., description="Name of the triggered signal or pattern")
    detail: str = Field(..., description="Contextual explanation of why the signal triggered")
    points: float = Field(..., description="Points contributed to the composite risk score")


class TransactionScoreRequest(BaseModel):
    """Payload for scoring a transaction against the FraudScope intelligence engine."""

    user_id: Optional[str] = Field(
        default=None,
        description="Identifier of the customer or card (used to look up historical baseline)",
        examples=["C123"],
    )
    amount: float = Field(
        ...,
        gt=0,
        description="Transaction amount in local currency (must be positive)",
        examples=[85000.0],
    )
    hour: int = Field(
        ...,
        ge=0,
        le=23,
        description="Hour of day when transaction occurs (0 - 23)",
        examples=[2],
    )
    device_id: str = Field(
        ...,
        min_length=1,
        description="Device / channel fingerprint or proxy",
        examples=["device_new"],
    )
    location: str = Field(
        ...,
        min_length=1,
        description="City or billing region code",
        examples=["Delhi"],
    )
    txn_count_10min: int = Field(
        default=1,
        ge=1,
        description="Number of transactions initiated in trailing 10 minutes",
        examples=[7],
    )
    seconds_since_prev: float = Field(
        default=86400.0,
        ge=0.0,
        description="Elapsed seconds since customer's previous transaction",
        examples=[120.0],
    )

    # Optional fields
    transaction_id: Optional[str] = Field(
        default=None,
        description="Optional unique identifier for transaction tracking",
        examples=["TXN-20260927-001"],
    )
    is_new_device: Optional[int] = Field(
        default=None,
        ge=0,
        le=1,
        description="Manual override flag: 1 if device is new for user, 0 if known",
        examples=[1],
    )
    is_new_location: Optional[int] = Field(
        default=None,
        ge=0,
        le=1,
        description="Manual override flag: 1 if location is outside usual area, 0 if known",
        examples=[1],
    )
    txn_count_1h: Optional[int] = Field(
        default=None,
        ge=1,
        description="Transactions in trailing 1 hour (defaults to txn_count_10min if omitted)",
        examples=[7],
    )
    currency: Optional[str] = Field(
        default="Rs",
        description="Currency symbol or abbreviation for reason explanations",
        examples=["Rs"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "C123",
                "amount": 85000,
                "hour": 2,
                "device_id": "device_new",
                "location": "Delhi",
                "txn_count_10min": 7,
                "seconds_since_prev": 120,
            }
        }
    )


class TransactionScoreResponse(BaseModel):
    """Structured risk assessment produced by FraudScope ML and rule engines."""

    transaction_id: str = Field(..., description="Unique transaction reference ID")
    risk_score: int = Field(..., ge=0, le=100, description="Composite risk score from 0 to 100")
    risk_level: str = Field(..., description="Risk tier: LOW, MEDIUM, or HIGH")
    ml_probability: float = Field(..., ge=0.0, le=1.0, description="Raw ML model fraud probability")
    ml_points: float = Field(..., description="Points contribution from ML model (max 60)")
    rule_points: float = Field(..., description="Points contribution from behavioural rules (max 40)")
    reasons: List[ReasonItem] = Field(..., description="Itemized factor breakdown explaining the score")
    summary: str = Field(..., description="Natural language executive summary of risk assessment")
    recommended_action: str = Field(..., description="Prescribed operational action")
    user_id: Optional[str] = Field(default=None, description="Customer or card identifier")
    features: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Complete feature vector passed to the ML classifier",
    )
