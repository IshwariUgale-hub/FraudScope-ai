from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.transaction import (
    TransactionDetailResponse,
    TransactionScoreRequest,
    TransactionScoreResponse,
)
from app.services.fraud_service import fraud_service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post(
    "/score",
    response_model=TransactionScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Transaction Risk & Persist",
    description=(
        "Scores a financial transaction using database-derived behavioural context and the "
        "existing FraudScope ML + deterministic rule engines. Persists transaction history and "
        "fraud assessment outcomes to PostgreSQL."
    ),
)
def score_transaction(
    payload: TransactionScoreRequest,
    db: Session = Depends(get_db),
) -> TransactionScoreResponse:
    return fraud_service.score_transaction(payload, db=db)


@router.get(
    "/{transaction_id}",
    response_model=TransactionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Transaction by ID",
    description="Retrieves a stored transaction and its complete fraud assessment details by transaction_id.",
)
def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
) -> TransactionDetailResponse:
    return fraud_service.get_transaction_by_id(transaction_id, db=db)
