"""Tests for the L1.5 semantic response cache (RediSearch HNSW)."""

from __future__ import annotations

import asyncio
import uuid
from typing import List

import pytest

from backend.core import cache
from backend.core.config import settings


pytestmark = [pytest.mark.needs_redis, pytest.mark.needs_redisearch]


def _uniq() -> str:
    return uuid.uuid4().hex[:12]


def _unit_vector(dim: int, seed: int) -> List[float]:
    """One-hot unit vector. Two calls with different seeds are orthogonal
    (cosine similarity == 0), which makes miss-assertions deterministic."""
    v = [0.0] * dim
    v[seed % dim] = 1.0
    return v


def _scaled_vector(dim: int, seed: int, scale: float) -> List[float]:
    """Scaled one-hot — same direction as _unit_vector(seed), different magnitude.
    Cosine similarity with the base vector is exactly 1.0."""
    v = _unit_vector(dim, seed)
    return [c * scale for c in v]


@pytest.fixture(autouse=True)
def _enable_semantic(monkeypatch):
    monkeypatch.setattr(settings, "SEMANTIC_CACHE_ENABLED", True)
    monkeypatch.setattr(settings, "SEMANTIC_CACHE_SHADOW_MODE", False)
    monkeypatch.setattr(settings, "SEMANTIC_EMBED_DIM", 8)
    yield


@pytest.fixture(autouse=True)
async def _cleanup_semantic_keys():
    yield
    client = await cache._get_client()
    if client is None:
        return
    for pattern in ("qcache:*", "rag:sem_answer:*"):
        cursor = 0
        while True:
            cursor, batch = await client.scan(cursor=cursor, match=pattern, count=500)
            if batch:
                await client.delete(*batch)
            if cursor == 0:
                break


async def test_semantic_cache_ready_returns_true():
    assert await cache.semantic_cache_ready() is True


async def test_index_is_bootstrapped_idempotently():
    assert await cache.semantic_cache_ready() is True
    cache._reset_semantic_state()
    assert await cache.semantic_cache_ready() is True


async def test_exact_vector_roundtrip_hits():
    profile = {"school": "columbia_college", "academic_year": "2026"}
    vec = _unit_vector(8, seed=42)
    payload = {"answer": "core classes are LitHum, CC, UW, and more.", "matches": []}

    wrote = await cache.set_semantic_response(
        query="what are the CC core classes?",
        embedding=vec,
        answer=payload,
        school="columbia_college",
        profile=profile,
    )
    assert wrote is True

    hit = await cache.get_semantic_response(
        query="literally any other phrasing",
        embedding=vec,
        school="columbia_college",
        profile=profile,
    )
    assert hit is not None
    assert hit["answer"] == payload["answer"]
    assert hit["_similarity"] >= settings.SEMANTIC_THRESHOLD


async def test_unrelated_vector_misses():
    profile = {"school": "columbia_college", "academic_year": "2026"}
    await cache.set_semantic_response(
        query="anchor q",
        embedding=_unit_vector(8, seed=0),
        answer={"answer": "A"},
        school="columbia_college",
        profile=profile,
    )
    result = await cache.get_semantic_response(
        query="different topic",
        embedding=_unit_vector(8, seed=4),
        school="columbia_college",
        profile=profile,
    )
    assert result is None


async def test_school_scoping_prevents_cross_school_hit():
    vec = _unit_vector(8, seed=7)
    await cache.set_semantic_response(
        query="what is lit hum",
        embedding=vec,
        answer={"answer": "cc-specific"},
        school="columbia_college",
        profile={"school": "columbia_college", "academic_year": "2026"},
    )
    miss = await cache.get_semantic_response(
        query="what is lit hum",
        embedding=vec,
        school="barnard",
        profile={"school": "barnard", "academic_year": "2026"},
    )
    assert miss is None


async def test_profile_hash_scoping_prevents_mismatch():
    vec = _unit_vector(8, seed=11)
    await cache.set_semantic_response(
        query="core requirements",
        embedding=vec,
        answer={"answer": "for 2026 cohort"},
        school="columbia_college",
        profile={"school": "columbia_college", "academic_year": "2026"},
    )
    miss = await cache.get_semantic_response(
        query="core requirements",
        embedding=vec,
        school="columbia_college",
        profile={"school": "columbia_college", "academic_year": "2024"},
    )
    assert miss is None


async def test_shadow_mode_does_not_serve(monkeypatch):
    monkeypatch.setattr(settings, "SEMANTIC_CACHE_SHADOW_MODE", True)

    profile = {"school": "columbia_college", "academic_year": "2026"}
    vec = _unit_vector(8, seed=13)
    await cache.set_semantic_response(
        query="shadow seed",
        embedding=vec,
        answer={"answer": "should not be served"},
        school="columbia_college",
        profile=profile,
    )
    result = await cache.get_semantic_response(
        query="shadow probe",
        embedding=vec,
        school="columbia_college",
        profile=profile,
    )
    assert result is None
    assert cache.stats()["semantic_shadow_hits"] >= 1


async def test_feature_flag_off_is_noop(monkeypatch):
    monkeypatch.setattr(settings, "SEMANTIC_CACHE_ENABLED", False)
    cache._reset_semantic_state()

    assert await cache.semantic_cache_ready() is False
    wrote = await cache.set_semantic_response(
        query="q", embedding=[0.1] * 8, answer={"answer": "a"},
        school="columbia_college",
        profile={"school": "columbia_college", "academic_year": "2026"},
    )
    assert wrote is False
    result = await cache.get_semantic_response(
        query="q", embedding=[0.1] * 8,
        school="columbia_college",
        profile={"school": "columbia_college", "academic_year": "2026"},
    )
    assert result is None


async def test_max_entries_cap_refuses_writes(monkeypatch):
    monkeypatch.setattr(settings, "SEMANTIC_MAX_ENTRIES", 0)
    cache._semantic_cap_cache["ok"] = False
    cache._semantic_cap_cache["checked_at"] = 1e18

    wrote = await cache.set_semantic_response(
        query=f"capped {_uniq()}", embedding=_unit_vector(8, seed=99),
        answer={"answer": "should not persist"},
        school="columbia_college",
        profile={"school": "columbia_college", "academic_year": "2026"},
    )
    assert wrote is False


async def test_oversize_answer_is_refused():
    huge = {"answer": "x" * (settings.SEMANTIC_MAX_ANSWER_BYTES + 100)}
    wrote = await cache.set_semantic_response(
        query="oversize",
        embedding=_unit_vector(8, seed=5),
        answer=huge,
        school="columbia_college",
        profile={"school": "columbia_college", "academic_year": "2026"},
    )
    assert wrote is False


async def test_answer_ttl_expires_entry(monkeypatch):
    monkeypatch.setattr(settings, "CACHE_TTL_SEMANTIC", 1)

    vec = _unit_vector(8, seed=77)
    profile = {"school": "columbia_college", "academic_year": "2026"}
    await cache.set_semantic_response(
        query="ttl seed",
        embedding=vec,
        answer={"answer": "short-lived"},
        school="columbia_college",
        profile=profile,
    )
    assert (await cache.get_semantic_response(
        query="ttl probe", embedding=vec,
        school="columbia_college", profile=profile,
    )) is not None

    await asyncio.sleep(1.5)
    miss = await cache.get_semantic_response(
        query="ttl probe after expire", embedding=vec,
        school="columbia_college", profile=profile,
    )
    assert miss is None
