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
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{DATABASE_PATH}"
    )
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
    AI_MODEL = os.environ.get("AI_MODEL", "gemini-1.5-flash")
    AI_TIMEOUT_SECONDS = int(os.environ.get("AI_TIMEOUT_SECONDS", "12"))

    # --- App ---
    DEBUG = _bool(os.environ.get("FLASK_DEBUG"), default=False)
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


CONFIG_MAP = {
    "default": Config,
    "testing": TestingConfig,
}
