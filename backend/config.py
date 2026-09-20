"""
Application configuration loaded from environment variables.
Copy .env.example to .env and adjust values for your environment.
"""
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _cors_origins(value):
    """Convert a comma-separated CORS allowlist into Flask-CORS origins."""
    if value is None:
        # The Vite development server is the only cross-origin client used
        # locally. Docker serves the built UI from this same application.
        return ("http://localhost:5173", "http://127.0.0.1:5173")

    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    return "*" if origins == ["*"] else tuple(origins)


def _database_uri():
    """Retrieve and normalize database URI for SQLAlchemy 2.0 + psycopg 3."""
    raw = os.environ.get("DATABASE_URL")
    if not raw:
        db_dir = os.environ.get(
            "DATABASE_DIR", os.path.join(BASE_DIR, "backend", "database")
        )
        db_path = os.environ.get(
            "DATABASE_PATH", os.path.join(db_dir, "compliance_scanner.db")
        )
        return f"sqlite:///{db_path}"

    cleaned = raw.strip().strip("'\"")
    # Normalize postgres driver for SQLAlchemy 2.0 + psycopg 3
    if cleaned.startswith("postgres://"):
        cleaned = "postgresql+psycopg://" + cleaned[len("postgres://"):]
    elif cleaned.startswith("postgresql://") and not cleaned.startswith("postgresql+"):
        cleaned = "postgresql+psycopg://" + cleaned[len("postgresql://"):]
    return cleaned


def _database_engine_options(uri: str):
    """Engine options optimized for Supabase transaction poolers and production databases."""
    options = {}
    if uri.startswith("postgresql"):
        # Supabase transaction pooler (port 6543) or Supavisor:
        # Transaction pooling mode resets connections after each transaction.
        # Prepared statements must be disabled (prepare_threshold=None) and
        # client-side pooling must use NullPool to avoid stale/broken socket hangs.
        if ":6543" in uri or "pooler.supabase.com" in uri:
            from sqlalchemy.pool import NullPool
            options["poolclass"] = NullPool
            options["connect_args"] = {
                "prepare_threshold": None,
            }
        else:
            options["pool_pre_ping"] = True
            options["pool_recycle"] = 300
    return options


class Config:
    # --- Core ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.environ.get("JWT_EXPIRES_HOURS", "24"))
    )
    JWT_ALGORITHM = "HS256"

    # --- Database ---
    DATABASE_DIR = os.environ.get(
        "DATABASE_DIR", os.path.join(BASE_DIR, "backend", "database")
    )
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", os.path.join(DATABASE_DIR, "compliance_scanner.db")
    )
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_ENGINE_OPTIONS = _database_engine_options(SQLALCHEMY_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Uploads / Reports ---
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(BASE_DIR, "backend", "uploads")
    )
    REPORT_FOLDER = os.environ.get(
        "REPORT_FOLDER", os.path.join(BASE_DIR, "backend", "reports")
    )
    MAX_CONTENT_LENGTH = int(
        os.environ.get("MAX_UPLOAD_SIZE_MB", "10")
    ) * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff", "webp"}

    # --- OCR ---
    TESSERACT_CMD = os.environ.get("TESSERACT_CMD", None)  # None => auto-detect on PATH
    OCR_MIN_WORD_CONFIDENCE = int(os.environ.get("OCR_MIN_WORD_CONFIDENCE", "45"))
    OCR_LOW_CONFIDENCE_THRESHOLD = int(os.environ.get("OCR_LOW_CONFIDENCE_THRESHOLD", "60"))

    # --- AI-Assisted Semantic Extraction ---
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini")  # gemini, openai, mock_testing
    AI_API_KEY = os.environ.get("AI_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    AI_MODEL = os.environ.get("AI_MODEL", "gemini-3.5-flash-lite")
    AI_TIMEOUT_SECONDS = int(os.environ.get("AI_TIMEOUT_SECONDS", "12"))

    # --- App ---
    DEBUG = _bool(os.environ.get("FLASK_DEBUG"), default=False)
    CORS_ORIGINS = _cors_origins(os.environ.get("CORS_ORIGINS"))


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False


CONFIG_MAP = {
    "default": Config,
    "testing": TestingConfig,
}
