import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Resolve the project root directory (the parent directory containing 'src' and 'models')
# Path: backend/app/core/config.py -> core -> app -> backend -> FRAUDSCOPE-AI
_current_file = Path(__file__).resolve()
PROJECT_ROOT = _current_file.parents[3]
BACKEND_DIR = _current_file.parents[2]

# Ensure project root and backend dir are in sys.path
for _path in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# Load environment variables from .env files if present
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")


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

    # Database configuration (PostgreSQL with SQLite fallback for zero-friction local dev/testing)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{PROJECT_ROOT}/fraudscope.db",
    )

    # CORS configuration for React frontend
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
