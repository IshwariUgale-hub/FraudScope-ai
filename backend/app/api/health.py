from typing import Dict
from fastapi import APIRouter

from app.db.session import check_db_connectivity

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Service & Database Health Check",
    description="Returns the operational status of the FRAUDSCOPE AI backend and database connectivity.",
)
def get_health() -> Dict[str, str]:
    db_ok = check_db_connectivity()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    }
