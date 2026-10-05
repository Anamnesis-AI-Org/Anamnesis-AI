"""Centralized configuration for Anamnesis-AI backend.

All settings are loaded from environment variables with sensible defaults.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend directory regardless of where uvicorn is launched.
_backend_root = Path(__file__).resolve().parents[1]
load_dotenv(_backend_root / ".env")
load_dotenv()


# ── Paths ─────────────────────────────────────────────────────────────────────

BACKEND_ROOT: Path = _backend_root


# ── Database ──────────────────────────────────────────────────────────────────

DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "sqlite+aiosqlite:///./anamnesis.db"
)

# Normalise common provider URL schemes (e.g. Supabase/Render hand back
# ``postgres://`` / ``postgresql://``) to the async SQLAlchemy driver, so a
# copy-pasted connection string works without manual edits.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL.removeprefix("postgres://")
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL.removeprefix("postgresql://")

# asyncpg (unlike psycopg) has no ``sslmode`` parameter — it expects ``ssl``.
# Supabase connection strings are copied with ``?sslmode=require``, which
# SQLAlchemy forwards verbatim to asyncpg and is rejected as an unexpected
# keyword argument. Translate it so the pooler URL works as-is.
if DATABASE_URL.startswith("postgresql+asyncpg://") and "sslmode=" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("sslmode=", "ssl=")

DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_CONNECT_TIMEOUT: int = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))


# ── LLM Providers ────────────────────────────────────────────────────────────

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_FALLBACK_MODELS: list[str] = [
    model.strip()
    for model in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-3.5-flash-lite,gemini-flash-latest",
    ).split(",")
    if model.strip()
]

_gemini_chain: list[str] = [GEMINI_MODEL, *GEMINI_FALLBACK_MODELS]
GEMINI_MODEL_CHAIN: tuple[str, ...] = tuple(dict.fromkeys(_gemini_chain))


# ── CORS ──────────────────────────────────────────────────────────────────────

CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
    ).split(",")
    if origin.strip()
]


# ── Application ───────────────────────────────────────────────────────────────

APP_ENV: str = os.getenv("APP_ENV", "development")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")  # "json" or "text"

MAX_INPUT_LENGTH: int = int(os.getenv("MAX_INPUT_LENGTH", "2000"))
MAX_CONCURRENT_SIMULATIONS: int = int(os.getenv("MAX_CONCURRENT_SIMULATIONS", "10"))

# Critic loop controls
CRITIC_CONFIDENCE_THRESHOLD: int = int(os.getenv("CRITIC_CONFIDENCE_THRESHOLD", "75"))
CRITIC_MAX_ITERATIONS: int = int(os.getenv("CRITIC_MAX_ITERATIONS", "2"))


# ── ChromaDB ──────────────────────────────────────────────────────────────────

CHROMA_DB_PATH: str = os.getenv(
    "CHROMA_DB_PATH",
    str(_backend_root / "chroma_db"),
)
