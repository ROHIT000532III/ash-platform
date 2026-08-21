from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def _load_env_file() -> None:
    """Load local development values without overriding real environment variables."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _positive_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _non_negative_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    ai_provider: str
    ai_fallback_provider: str | None
    ollama_base_url: str
    ollama_model: str
    request_timeout_seconds: int
    request_retries: int
    database_path: Path
    context_message_limit: int
    auth_token_secret: str
    auth_session_days: int
    workspace_root: Path


def get_settings() -> Settings:
    _load_env_file()
    provider = os.getenv("AI_PROVIDER", "ollama").strip().lower() or "ollama"
    fallback_provider = os.getenv("AI_FALLBACK_PROVIDER", "").strip().lower()
    if fallback_provider not in ("", "demo"):
        fallback_provider = ""

    return Settings(
        ai_provider=provider,
        ai_fallback_provider=fallback_provider or None,
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2").strip() or "llama3.2",
        request_timeout_seconds=_positive_int("AI_REQUEST_TIMEOUT_SECONDS", 30),
        request_retries=_non_negative_int("AI_REQUEST_RETRIES", 1),
        database_path=Path(
            os.getenv(
                "ASH_DATABASE_PATH",
                str(Path(__file__).resolve().parents[2] / "data" / "ash_ai.db"),
            )
        ),
        context_message_limit=_positive_int("AI_CONTEXT_MESSAGE_LIMIT", 30),
        auth_token_secret=os.getenv("AUTH_TOKEN_SECRET", "").strip() or secrets.token_urlsafe(32),
        auth_session_days=_positive_int("AUTH_SESSION_DAYS", 14),
        workspace_root=Path(os.getenv("ASH_WORKSPACE_ROOT", str(Path(__file__).resolve().parents[2] / "workspace"))),
    )
