"""
Application configuration.

Loads settings from environment variables (with optional .env files).
Uses pydantic-settings when available; falls back to a plain object otherwise
so the backend still imports in environments where pydantic-settings is not
installed (e.g. lightweight scripts).
"""

from __future__ import annotations

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        # Redis (used by backend.core.cache)
        REDIS_URL: Optional[str] = None

        # OpenAI / LLM providers
        OPENAI_API_KEY: Optional[str] = None
        LLM_PROVIDER: str = "openai"

        # Database
        DATABASE_URL: Optional[str] = None

        # Embeddings
        EMBED_MODEL: str = "text-embedding-3-small"

        # RAG
        TOP_K: int = 8
        MAX_CONTEXT_CHARS: int = 12000
        MAX_HISTORY_MESSAGES: int = 10

        model_config = SettingsConfigDict(
            env_file=(".env", "backend/scripts/embedder/.env"),
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore",
        )

    settings = Settings()  # type: ignore[call-arg]

except ImportError:
    class _Settings:
        REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
        OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
        LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
        DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
        EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")
        TOP_K: int = int(os.getenv("TOP_K", "8"))
        MAX_CONTEXT_CHARS: int = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))
        MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))

    settings = _Settings()  # type: ignore[assignment]
