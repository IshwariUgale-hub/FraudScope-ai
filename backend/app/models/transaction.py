from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)

from app.db.base import Base


class Transaction(Base):
    """SQLAlchemy model representing a stored financial transaction and its FraudScope risk score."""

    __tablename__ = "transactions"

    # Primary key identifier
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Unique external transaction reference ID
    transaction_id = Column(String(64), unique=True, index=True, nullable=False)

    # User / Card identifier
    user_id = Column(String(64), index=True, nullable=False)

    # Financial transaction attributes
    amount = Column(Float, nullable=False)
    timestamp = Column(BigInteger, nullable=False, index=True)
    device_id = Column(String(128), nullable=False)
    location = Column(String(128), nullable=False)
    currency = Column(String(16), nullable=False, default="Rs")

    # Backend-derived behavioural context
    txn_count_10min = Column(Integer, nullable=False, default=1)
    txn_count_1h = Column(Integer, nullable=True)
    seconds_since_prev = Column(Float, nullable=False, default=86400.0)
    is_new_device = Column(Integer, nullable=True, default=0)
    is_new_location = Column(Integer, nullable=True, default=0)

    # Risk assessment results
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(16), nullable=False)
    ml_probability = Column(Float, nullable=False)
    ml_points = Column(Float, nullable=False, default=0.0)
    rule_points = Column(Float, nullable=False, default=0.0)
    recommended_action = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)

    # Granular breakdown reasons and feature vector for auditability & behavioral analysis
    reasons = Column(JSON, nullable=True)
    features = Column(JSON, nullable=True)

    # Audit timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Indexes for optimal querying of user transaction history and time windows
    __table_args__ = (
        Index("ix_transactions_user_timestamp", "user_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, txn_id='{self.transaction_id}', "
            f"user_id='{self.user_id}', amount={self.amount}, "
            f"score={self.risk_score}, level='{self.risk_level}')>"
        )
