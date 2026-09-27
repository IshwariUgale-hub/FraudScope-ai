import os
import sys
from pathlib import Path

# Resolve the project root directory (the parent directory containing 'src' and 'models')
# Path: backend/app/core/config.py -> core -> app -> backend -> FRAUDSCOPE-AI
_current_file = Path(__file__).resolve()
PROJECT_ROOT = _current_file.parents[3]

# Verify and ensure project root is on sys.path so that 'src.*' imports function properly
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class Settings:
    """Application settings and configuration parameters."""

    PROJECT_NAME: str = "FRAUDSCOPE AI Backend"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "Explainable Real-Time Financial Fraud Intelligence & Risk Scoring Platform API"
    )
    API_V1_PREFIX: str = "/api/v1"

    # Paths to existing ML artifacts
    PROJECT_ROOT: Path = PROJECT_ROOT
    MODEL_PATH: str = os.getenv(
        "FRAUDSCOPE_MODEL_PATH",
        str(PROJECT_ROOT / "models" / "fraud_model.pkl"),
    )
    PROFILES_PATH: str = os.getenv(
        "FRAUDSCOPE_PROFILES_PATH",
        str(PROJECT_ROOT / "models" / "profiles.json"),
    )
    METRICS_PATH: str = os.getenv(
        "FRAUDSCOPE_METRICS_PATH",
        str(PROJECT_ROOT / "models" / "metrics.json"),
    )

    # CORS configuration for future React frontend
    # Allows comma-separated string from environment, or sensible local dev defaults
    _cors_env = os.getenv("CORS_ORIGINS", "")
    if _cors_env.strip():
        CORS_ORIGINS: list[str] = [origin.strip() for origin in _cors_env.split(",") if origin.strip()]
    else:
        CORS_ORIGINS: list[str] = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]


settings = Settings()
