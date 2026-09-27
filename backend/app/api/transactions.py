from fastapi import APIRouter, status

from app.schemas.transaction import TransactionScoreRequest, TransactionScoreResponse
from app.services.fraud_service import fraud_service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post(
    "/score",
    response_model=TransactionScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Transaction Risk",
    description=(
        "Scores a financial transaction using the existing FraudScope ML classifier and "
        "deterministic rule engine. Returns an explainable composite risk score, risk tier, "
        "reasons, and recommended operational action."
    ),
)
def score_transaction(payload: TransactionScoreRequest) -> TransactionScoreResponse:
    return fraud_service.score_transaction(payload)
