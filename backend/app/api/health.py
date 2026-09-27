from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Service Health Check",
    description="Returns the operational status of the FRAUDSCOPE AI backend.",
)
def get_health() -> dict[str, str]:
    return {"status": "ok"}
