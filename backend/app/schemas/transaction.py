from __future__ import annotations

from datetime import datetime
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

    # Contextual behavioral fields (Optional; prefer database-derived when user history exists)
    timestamp: Optional[int] = Field(
        default=None,
        description="Unix timestamp of transaction (defaults to current time if omitted)",
        examples=[1727448000],
    )
    txn_count_10min: Optional[int] = Field(
        default=None,
        ge=1,
        description="Transactions in last 10 minutes (defaults to DB history or 1 on cold-start)",
        examples=[7],
    )
    seconds_since_prev: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Seconds since previous transaction (defaults to DB history or 86400 on cold-start)",
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
        description="Transactions in trailing 1 hour (defaults to DB history)",
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


class TransactionDetailResponse(BaseModel):
    """Full detail of a stored transaction record."""

    id: int = Field(..., description="Internal database ID")
    transaction_id: str = Field(..., description="Unique transaction reference ID")
    user_id: str = Field(..., description="Customer or card identifier")
    amount: float = Field(..., description="Transaction amount")
    timestamp: int = Field(..., description="Transaction unix timestamp")
    device_id: str = Field(..., description="Device identifier")
    location: str = Field(..., description="Location")
    currency: str = Field(..., description="Currency symbol")
    txn_count_10min: int = Field(..., description="Evaluated 10-minute transaction count")
    txn_count_1h: Optional[int] = Field(None, description="Evaluated 1-hour transaction count")
    seconds_since_prev: float = Field(..., description="Evaluated seconds since previous transaction")
    is_new_device: Optional[int] = Field(None, description="New device flag (0 or 1)")
    is_new_location: Optional[int] = Field(None, description="New location flag (0 or 1)")
    risk_score: int = Field(..., description="Assessed risk score (0-100)")
    risk_level: str = Field(..., description="Risk tier")
    ml_probability: float = Field(..., description="ML fraud probability")
    ml_points: float = Field(..., description="ML points contribution")
    rule_points: float = Field(..., description="Rule points contribution")
    recommended_action: str = Field(..., description="Recommended action")
    summary: str = Field(..., description="Explanation summary")
    reasons: List[ReasonItem] = Field(default_factory=list, description="List of reasons")
    features: Optional[Dict[str, Any]] = Field(default=None, description="Computed features")
    created_at: Optional[datetime] = Field(None, description="Database record creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class UserTransactionsResponse(BaseModel):
    """Response containing list of recent transactions for a given user."""

    user_id: str = Field(..., description="User ID queried")
    total_transactions: int = Field(..., description="Total number of stored transactions for this user")
    transactions: List[TransactionDetailResponse] = Field(..., description="List of transaction records")
