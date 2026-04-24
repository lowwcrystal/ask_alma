"""
Application configuration.

All settings are driven from environment variables (with optional .env files).
Uses pydantic-settings when available; falls back to a plain object otherwise
so the backend still imports in environments where pydantic-settings is not
installed (e.g. lightweight offline scripts).
"""

from __future__ import annotations

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        # Redis connection
        REDIS_URL: Optional[str] = None
        REDIS_MAX_CONNECTIONS: int = 20
        REDIS_SOCKET_TIMEOUT: float = 2.0
        REDIS_SOCKET_CONNECT_TIMEOUT: float = 2.0
        REDIS_POOL_WAIT_TIMEOUT: float = 2.0  # max seconds to block waiting for a free conn

        # Cache TTLs (seconds)
        CACHE_TTL_EXACT: int = 3600         # Layer 1: Exact query response — 1 hour
        CACHE_TTL_EMBEDDING: int = 86400    # Layer 2: Query embedding     — 24 hours
        CACHE_TTL_CHUNKS: int = 21600       # Layer 3: Retrieved chunks    — 6 hours
        CACHE_TTL_LLM: int = 1800           # Layer 4: LLM response        — 30 minutes

        # Cache health
        CACHE_HIT_RATE_ALERT_THRESHOLD: float = 0.4  # warn when hit rate drops below
        CACHE_METRICS_SAMPLE_EVERY: int = 100        # check hit rate every N lookups

        # Circuit breaker
        CIRCUIT_BREAKER_FAILURES: int = 5    # trip after N failures
        CIRCUIT_BREAKER_WINDOW_SECONDS: int = 60   # ...within this window
        CIRCUIT_BREAKER_COOLDOWN_SECONDS: int = 60  # disable cache for this long

        # Semantic response cache (L1.5)
        SEMANTIC_CACHE_ENABLED: bool = False
        SEMANTIC_CACHE_SHADOW_MODE: bool = False
        SEMANTIC_THRESHOLD: float = 0.95
        SEMANTIC_THRESHOLD_WARN: float = 0.90
        CACHE_TTL_SEMANTIC: int = 21600
        SEMANTIC_MAX_ENTRIES: int = 50000
        SEMANTIC_MAX_ANSWER_BYTES: int = 65536
        SEMANTIC_EMBED_DIM: int = 1536

        # OpenAI / LLM providers
        OPENAI_API_KEY: Optional[str] = None
        LLM_PROVIDER: str = "openai"

        # Database
        DATABASE_URL: Optional[str] = None

        # Embeddings
        EMBED_MODEL: str = "text-embedding-3-small"

        # RAG
        TOP_K: int = 6
        MAX_CONTEXT_CHARS: int = 5000
        MAX_HISTORY_MESSAGES: int = 6

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
        REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
        REDIS_SOCKET_TIMEOUT: float = float(os.getenv("REDIS_SOCKET_TIMEOUT", "2.0"))
        REDIS_SOCKET_CONNECT_TIMEOUT: float = float(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "2.0"))
        REDIS_POOL_WAIT_TIMEOUT: float = float(os.getenv("REDIS_POOL_WAIT_TIMEOUT", "2.0"))
        CACHE_TTL_EXACT: int = int(os.getenv("CACHE_TTL_EXACT", "3600"))
        CACHE_TTL_EMBEDDING: int = int(os.getenv("CACHE_TTL_EMBEDDING", "86400"))
        CACHE_TTL_CHUNKS: int = int(os.getenv("CACHE_TTL_CHUNKS", "21600"))
        CACHE_TTL_LLM: int = int(os.getenv("CACHE_TTL_LLM", "1800"))
        CACHE_HIT_RATE_ALERT_THRESHOLD: float = float(os.getenv("CACHE_HIT_RATE_ALERT_THRESHOLD", "0.4"))
        CACHE_METRICS_SAMPLE_EVERY: int = int(os.getenv("CACHE_METRICS_SAMPLE_EVERY", "100"))
        CIRCUIT_BREAKER_FAILURES: int = int(os.getenv("CIRCUIT_BREAKER_FAILURES", "5"))
        CIRCUIT_BREAKER_WINDOW_SECONDS: int = int(os.getenv("CIRCUIT_BREAKER_WINDOW_SECONDS", "60"))
        CIRCUIT_BREAKER_COOLDOWN_SECONDS: int = int(os.getenv("CIRCUIT_BREAKER_COOLDOWN_SECONDS", "60"))
        SEMANTIC_CACHE_ENABLED: bool = os.getenv("SEMANTIC_CACHE_ENABLED", "false").lower() == "true"
        SEMANTIC_CACHE_SHADOW_MODE: bool = os.getenv("SEMANTIC_CACHE_SHADOW_MODE", "false").lower() == "true"
        SEMANTIC_THRESHOLD: float = float(os.getenv("SEMANTIC_THRESHOLD", "0.95"))
        SEMANTIC_THRESHOLD_WARN: float = float(os.getenv("SEMANTIC_THRESHOLD_WARN", "0.90"))
        CACHE_TTL_SEMANTIC: int = int(os.getenv("CACHE_TTL_SEMANTIC", "21600"))
        SEMANTIC_MAX_ENTRIES: int = int(os.getenv("SEMANTIC_MAX_ENTRIES", "50000"))
        SEMANTIC_MAX_ANSWER_BYTES: int = int(os.getenv("SEMANTIC_MAX_ANSWER_BYTES", "65536"))
        SEMANTIC_EMBED_DIM: int = int(os.getenv("SEMANTIC_EMBED_DIM", "1536"))
        OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
        LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
        DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
        EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")
        TOP_K: int = int(os.getenv("TOP_K", "6"))
        MAX_CONTEXT_CHARS: int = int(os.getenv("MAX_CONTEXT_CHARS", "5000"))
        MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", "6"))

    settings = _Settings()  # type: ignore[assignment]
