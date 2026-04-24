"""
Shared test plumbing.

Tests that exercise the real cache are marked `@pytest.mark.needs_redis` and
are skipped when REDIS_URL is unreachable. Failure-mode tests don't carry that
marker (they simulate Redis outages via monkeypatching) and always run.

Also resets cache metrics + circuit-breaker state between tests so
hit/miss/error assertions are deterministic.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# --------------------------------------------------------------------------
# Redis availability probe — only matters for tests marked `needs_redis`.
# --------------------------------------------------------------------------

def _redis_reachable(url: str) -> bool:
    if not url:
        return False
    try:
        import redis  # sync client — we only need a fast probe
        client = redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        return bool(client.ping())
    except Exception:  # noqa: BLE001
        return False


def _redisearch_available(url: str) -> bool:
    if not url:
        return False
    try:
        import redis
        client = redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        modules = client.execute_command("MODULE", "LIST")
        for entry in modules or []:
            if isinstance(entry, (list, tuple)):
                for item in entry:
                    if isinstance(item, (bytes, bytearray)) and item.lower() == b"search":
                        return True
                    if isinstance(item, str) and item.lower() == "search":
                        return True
        return False
    except Exception:  # noqa: BLE001
        return False


_REDIS_URL = os.environ.get("REDIS_URL", "")
_REDIS_OK = _redis_reachable(_REDIS_URL)
_REDISEARCH_OK = _REDIS_OK and _redisearch_available(_REDIS_URL)


def pytest_collection_modifyitems(config, items):
    """Skip `needs_redis` / `needs_redisearch` tests when not available."""
    skip_no_redis = pytest.mark.skip(
        reason=f"REDIS_URL not reachable ({_REDIS_URL!r})",
    )
    skip_no_search = pytest.mark.skip(
        reason="RediSearch module not available on the configured Redis",
    )
    for item in items:
        if "needs_redis" in item.keywords and not _REDIS_OK:
            item.add_marker(skip_no_redis)
        if "needs_redisearch" in item.keywords and not _REDISEARCH_OK:
            item.add_marker(skip_no_search)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "needs_redis: test requires a live Redis connection via REDIS_URL",
    )
    config.addinivalue_line(
        "markers", "needs_redisearch: test requires the RediSearch module on the Redis instance",
    )


# --------------------------------------------------------------------------
# Per-test state reset.
# --------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_cache_state():
    """Reset per-process state between tests so assertions are deterministic."""
    from backend.core import cache

    cache.reset_metrics()
    cache._circuit.failure_times.clear()
    cache._circuit.opened_at = None
    cache._reset_semantic_state()
    yield


# --------------------------------------------------------------------------
# Redis pool lifecycle.
#
# pytest-asyncio 1.x manages the event loop itself; we just make sure the
# pool is torn down at the end of the session. (If pytest-asyncio uses a
# function-scoped loop, the session loop scope configured in pytest.ini
# avoids "Event loop is closed" errors from the reused async client.)
# --------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
async def _close_cache_at_end():
    yield
    from backend.core import cache
    try:
        await cache.close_cache()
    except Exception:  # noqa: BLE001
        pass
