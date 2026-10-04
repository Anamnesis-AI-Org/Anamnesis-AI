"""Structured logging configuration for Anamnesis-AI.

Provides JSON-formatted logs in production and human-readable logs in
development.  Call ``setup_logging()`` once at application startup.
"""

import json
import logging
import sys
from datetime import datetime, timezone

from app.config import LOG_LEVEL, LOG_FORMAT


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "scenario_id"):
            log_entry["scenario_id"] = record.scenario_id
        if hasattr(record, "agent"):
            log_entry["agent"] = record.agent
        return json.dumps(log_entry, default=str)


class DevFormatter(logging.Formatter):
    """Coloured, human-readable formatter for local development."""

    COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[35m",  # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = f"{color}{ts} {record.levelname:<8}{self.RESET}"
        msg = record.getMessage()
        if record.exc_info and record.exc_info[0] is not None:
            msg += "\n" + self.formatException(record.exc_info)
        return f"{prefix} [{record.name}] {msg}"


def setup_logging() -> None:
    """Configure the root logger based on ``LOG_FORMAT`` and ``LOG_LEVEL``."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Remove existing handlers to avoid duplication on reload.
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(DevFormatter())

    root.addHandler(handler)

    # Quieten noisy third-party loggers.
    for name in ("httpcore", "httpx", "chromadb", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)

    # google-genai logs an "automatic function calling is not recommended"
    # recommendation on every plain generate_content call. Keep only its real
    # errors so production logs stay clean. The SDK registers the logger under
    # both the module path and the normalized package name.
    for name in ("google.genai", "google_genai"):
        logging.getLogger(name).setLevel(logging.ERROR)
