"""
Phase 5 - failure mode tests for backend/core/cache.py.

No network required. Uses monkeypatching to simulate Redis outages.
These tests MUST pass in any environment (they're the safety net).
"""

from __future__ import annotations

import asyncio

import pytest

from backend.core import cache
from backend.core.config import settings


pytestmark = pytest.mark.asyncio


# --- Override the session-wide `_require_redis` skip for this file.
# These tests don't need Redis at all; they fake the client.
@pytest.fixture(scope="module", autouse=True)
def _skip_session_redis_requirement(request):
    # Ensure a clean slate for each test in this module.
    yield


@pytest.fixture(autouse=True)
def _fresh_state():
    """Each test starts with clean metrics + closed circuit + no cached client."""
    cache.reset_metrics()
    cache._circuit.failure_times.clear()
    cache._circuit.opened_at = None
    # Force the client to be rebuilt next call (we'll be monkeypatching).
    cache._redis_client = None
    yield
    cache._redis_client = None


# ---------------------------------------------------------------------------
# 1. Fail-open when REDIS_URL not set
# ---------------------------------------------------------------------------

async def test_cache_is_disabled_when_redis_url_missing(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", None)
    assert cache.cache_enabled() is False
    # Every read returns None; every write returns False. No exceptions.
    assert await cache.get_embedding("anything") is None
    assert await cache.set_embedding("anything", [0.1]) is False
    assert await cache.ping() is False
    pre = await cache.prefetch_layers(
        query="q", user_id=None, conversation_id=None,
        profile=None, history_len=0, school=None,
    )
    assert pre == {"exact": None, "embedding": None, "chunks": None}


# ---------------------------------------------------------------------------
# 2. Errors are swallowed; caller sees safe defaults
# ---------------------------------------------------------------------------

class _ExplodingClient:
    """Redis client stand-in that throws on every operation."""

    async def get(self, *_a, **_kw):
        raise ConnectionError("redis exploded")

    async def set(self, *_a, **_kw):
        raise ConnectionError("redis exploded")

    async def delete(self, *_a, **_kw):
        raise ConnectionError("redis exploded")

    async def ping(self):
        raise ConnectionError("redis exploded")

    def pipeline(self, *_a, **_kw):
        return _ExplodingPipeline()

    async def aclose(self):
        return None


class _ExplodingPipeline:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    def get(self, *_a, **_kw):
        return self

    def set(self, *_a, **_kw):
        return self

    async def execute(self):
        raise ConnectionError("redis exploded")


async def test_exploding_redis_does_not_crash_callers(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake-host:6379")
    monkeypatch.setattr(cache, "_get_client", _make_fake_getter(_ExplodingClient()))

    # All of these would raise without the safe_* wrappers
    assert await cache.get_embedding("x") is None
    assert await cache.set_embedding("x", [0.1]) is False
    assert await cache.get_chunks("x", "barnard") is None
    assert await cache.get_exact_response("x", "u", "c", None, 0) is None

    s = cache.stats()
    assert s["errors"] >= 3, f"expected errors recorded in stats, got {s}"


# ---------------------------------------------------------------------------
# 3. Circuit breaker trips after N failures, cools down, then auto-recovers
# ---------------------------------------------------------------------------

async def test_circuit_breaker_trips_and_cools_down(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake-host:6379")
    monkeypatch.setattr(settings, "CIRCUIT_BREAKER_FAILURES", 3)
    monkeypatch.setattr(settings, "CIRCUIT_BREAKER_WINDOW_SECONDS", 60)
    monkeypatch.setattr(settings, "CIRCUIT_BREAKER_COOLDOWN_SECONDS", 1)
    monkeypatch.setattr(cache, "_get_client", _make_fake_getter(_ExplodingClient()))

    # Rack up failures
    for _ in range(3):
        await cache.get_embedding("trigger-failure")

    assert cache._circuit.is_open(), "breaker should be open after threshold failures"
    assert cache.cache_enabled() is False, "cache must short-circuit while breaker open"

    # While the breaker is open, further calls do NOT hit Redis at all
    # (so errors counter should not grow further).
    errors_before = cache.stats()["errors"]
    for _ in range(5):
        await cache.get_embedding("during-cooldown")
    assert cache.stats()["errors"] == errors_before, "breaker must isolate Redis from callers"

    # Wait out the cooldown (1s configured above)
    await asyncio.sleep(1.1)
    # is_open() has the side effect of resetting the breaker once cooldown elapsed
    assert cache._circuit.is_open() is False
    assert cache.cache_enabled() is True


# ---------------------------------------------------------------------------
# 4. ping() returns False on failure (never raises)
# ---------------------------------------------------------------------------

async def test_ping_swallows_errors(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake-host:6379")
    monkeypatch.setattr(cache, "_get_client", _make_fake_getter(_ExplodingClient()))
    assert await cache.ping() is False


# ---------------------------------------------------------------------------
# 5. Malformed cached payloads decode to None (not an exception)
# ---------------------------------------------------------------------------

class _CorruptClient:
    async def get(self, *_a, **_kw):
        return b"not-valid-json{{{"

    async def set(self, *_a, **_kw):
        return True

    def pipeline(self, *_a, **_kw):
        return _CorruptPipeline()

    async def ping(self):
        return True

    async def aclose(self):
        return None


class _CorruptPipeline:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    def get(self, *_a, **_kw):
        return self

    async def execute(self):
        return [b"not-valid-json{{{", b"garbage", b"\x00\x01"]


async def test_corrupt_payloads_return_none(monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "redis://fake-host:6379")
    monkeypatch.setattr(cache, "_get_client", _make_fake_getter(_CorruptClient()))
    assert await cache.get_embedding("x") is None
    pre = await cache.prefetch_layers(
        query="q", user_id="u", conversation_id="c",
        profile=None, history_len=0, school=None,
    )
    assert pre == {"exact": None, "embedding": None, "chunks": None}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_getter(client):
    async def _fake_get_client():
        return client
    return _fake_get_client
