from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.transaction import UserTransactionsResponse
from app.services.fraud_service import fraud_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/{user_id}/transactions",
    response_model=UserTransactionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User Transaction History",
    description="Retrieves chronological recent transactions and risk scores for a specific user.",
)
def get_user_transactions(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of records to return"),
    skip: int = Query(default=0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
) -> UserTransactionsResponse:
    total, txns = fraud_service.get_user_transactions(user_id, db=db, limit=limit, skip=skip)
    return UserTransactionsResponse(
        user_id=user_id,
        total_transactions=total,
        transactions=txns,
    )
