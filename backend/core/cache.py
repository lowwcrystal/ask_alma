"""
Redis cache client (placeholder).

This module is intentionally minimal until the multi-layer caching
implementation (exact query / embedding / chunks / LLM response) lands.

Importing this module must NOT fail when `redis` is not installed — instead,
`redis_client` is set to None and callers can fall back to no-op behavior.
"""

from __future__ import annotations

from typing import Optional

from backend.core.config import settings

redis_client: Optional[object] = None

try:
    import redis.asyncio as _redis  # type: ignore

    if settings.REDIS_URL:
        redis_client = _redis.from_url(
            settings.REDIS_URL,
            decode_responses=False,
            max_connections=20,
        )
except ImportError:
    redis_client = None
