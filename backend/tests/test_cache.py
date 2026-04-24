"""

Runs against a live Redis (CI service container or Redis Cloud).
Every test cleans up its own keys; nothing persists across runs.
"""

from __future__ import annotations

import pytest

from backend.core import cache


pytestmark = pytest.mark.needs_redis


async def test_ping_succeeds():
    assert await cache.ping() is True


def test_normalize_query_is_case_punct_whitespace_insensitive():
    assert cache.normalize_query("  What is X??  ") == "what is x"
    assert cache.normalize_query("HELLO, World!") == cache.normalize_query("hello world")
    assert cache.normalize_query("") == ""


def test_embedding_key_stable_and_distinct():
    a = cache.key_embedding("what classes?")
    b = cache.key_embedding("  WHAT classes?? ")
    c = cache.key_embedding("what class?")
    assert a == b, "equivalent queries must collide"
    assert a != c, "distinct queries must not collide"


def test_chunks_key_depends_on_school():
    assert cache.key_chunks("q", "barnard") != cache.key_chunks("q", "columbia_college")
    assert cache.key_chunks("q", None) != cache.key_chunks("q", "barnard")
    assert cache.key_chunks("Q??", "barnard") == cache.key_chunks("q", "barnard")


def test_exact_key_personalizes_by_user_conv_history():
    base = {"school": "barnard", "academic_year": "2026"}
    k0 = cache.key_exact("q", "user-A", "conv-1", base, 0)
    assert k0 != cache.key_exact("q", "user-B", "conv-1", base, 0), "user isolation"
    assert k0 != cache.key_exact("q", "user-A", "conv-2", base, 0), "conversation isolation"
    assert k0 != cache.key_exact("q", "user-A", "conv-1", base, 1), "history_len isolation"
    assert k0 != cache.key_exact("q", "user-A", "conv-1", {**base, "school": "columbia_college"}, 0), "profile isolation"


def test_llm_key_depends_on_chunks_fingerprint():
    fp_a = cache.chunks_fingerprint([{"id": 1}, {"id": 2}])
    fp_b = cache.chunks_fingerprint([{"id": 3}])
    k_a = cache.key_llm("q", "u", "c", {"school": "barnard"}, 0, fp_a)
    k_b = cache.key_llm("q", "u", "c", {"school": "barnard"}, 0, fp_b)
    assert k_a != k_b, "different chunks => different L4 key"


async def test_l2_embedding_roundtrip_and_normalization():
    query = f"pytest embed {id(test_l2_embedding_roundtrip_and_normalization)}"
    vector = [0.1, 0.2, 0.3, 0.4]
    try:
        assert await cache.set_embedding(query, vector) is True
        assert await cache.get_embedding(query) == vector
        # Case/punctuation/whitespace variants collapse to the same key
        assert await cache.get_embedding(f"  {query.upper()}!!! ") == vector
    finally:
        client = await cache._get_client()
        if client:
            await client.delete(cache.key_embedding(query))


async def test_l2_miss_returns_none():
    assert await cache.get_embedding(f"missing-{id(test_l2_miss_returns_none)}") is None


# ---------------------------------------------------------------------------
# L3 — chunks cache scoped by school
# ---------------------------------------------------------------------------

async def test_l3_school_scoping_is_hard():
    q = f"pytest chunks {id(test_l3_school_scoping_is_hard)}"
    chunks = [
        {"id": 101, "content": "Barnard info", "similarity": 0.9, "source": "barnard"},
    ]
    try:
        assert await cache.set_chunks(q, "barnard", chunks) is True
        assert await cache.get_chunks(q, "barnard") == chunks
        # Different school must miss
        assert await cache.get_chunks(q, "columbia_college") is None
        # No-school must also miss
        assert await cache.get_chunks(q, None) is None
    finally:
        client = await cache._get_client()
        if client:
            await client.delete(
                cache.key_chunks(q, "barnard"),
                cache.key_chunks(q, "columbia_college"),
                cache.key_chunks(q, None),
            )


async def test_l1_no_cross_user_leakage():
    q = f"pytest exact {id(test_l1_no_cross_user_leakage)}"
    profile = {"school": "barnard"}
    payload = {"answer": "Yes.", "matches": []}
    try:
        assert await cache.set_exact_response(q, "user-A", "conv-1", profile, 0, payload) is True
        assert await cache.get_exact_response(q, "user-A", "conv-1", profile, 0) == payload
        # Different user -> miss
        assert await cache.get_exact_response(q, "user-B", "conv-1", profile, 0) is None
        # Different history_len -> miss
        assert await cache.get_exact_response(q, "user-A", "conv-1", profile, 1) is None
        # Different conversation -> miss
        assert await cache.get_exact_response(q, "user-A", "conv-2", profile, 0) is None
    finally:
        client = await cache._get_client()
        if client:
            await client.delete(cache.key_exact(q, "user-A", "conv-1", profile, 0))


# ---------------------------------------------------------------------------
# L4 — LLM cache invalidates on chunk changes
# ---------------------------------------------------------------------------

async def test_l4_chunks_fingerprint_invalidation():
    q = f"pytest llm {id(test_l4_chunks_fingerprint_invalidation)}"
    profile = {"school": "barnard"}
    chunks_v1 = [{"id": 1}, {"id": 2}]
    chunks_v2 = [{"id": 1}, {"id": 999}]  # different fingerprint
    try:
        assert await cache.set_llm_response(q, "u", "c", profile, 0, chunks_v1, "Answer v1") is True
        assert await cache.get_llm_response(q, "u", "c", profile, 0, chunks_v1) == "Answer v1"
        # New chunks => key busts
        assert await cache.get_llm_response(q, "u", "c", profile, 0, chunks_v2) is None
    finally:
        client = await cache._get_client()
        if client:
            fp_v1 = cache.chunks_fingerprint(chunks_v1)
            fp_v2 = cache.chunks_fingerprint(chunks_v2)
            await client.delete(
                cache.key_llm(q, "u", "c", profile, 0, fp_v1),
                cache.key_llm(q, "u", "c", profile, 0, fp_v2),
            )


# ---------------------------------------------------------------------------
# prefetch — single pipeline, three hits
# ---------------------------------------------------------------------------

async def test_prefetch_returns_all_three_layers():
    q = f"pytest prefetch {id(test_prefetch_returns_all_three_layers)}"
    profile = {"school": "barnard"}
    vector = [0.1, 0.2]
    chunks = [{"id": 1, "content": "x", "similarity": 0.9, "source": "barnard"}]
    payload = {"answer": "cached", "matches": chunks}
    try:
        await cache.set_embedding(q, vector)
        await cache.set_chunks(q, "barnard", chunks)
        await cache.set_exact_response(q, "u", "c", profile, 0, payload)

        pre = await cache.prefetch_layers(
            query=q,
            user_id="u",
            conversation_id="c",
            profile=profile,
            history_len=0,
            school="barnard",
        )
        assert pre["embedding"] == vector
        assert pre["chunks"] == chunks
        assert pre["exact"] == payload

        # And metrics reflect 3 hits
        s = cache.stats()
        assert s["hits"]["embedding"] >= 1
        assert s["hits"]["chunks"] >= 1
        assert s["hits"]["exact"] >= 1
    finally:
        client = await cache._get_client()
        if client:
            await client.delete(
                cache.key_embedding(q),
                cache.key_chunks(q, "barnard"),
                cache.key_exact(q, "u", "c", profile, 0),
            )


async def test_prefetch_all_miss_increments_miss_counters():
    q = f"pytest prefetch-miss {id(test_prefetch_all_miss_increments_miss_counters)}"
    pre = await cache.prefetch_layers(
        query=q,
        user_id="nobody",
        conversation_id="nowhere",
        profile=None,
        history_len=0,
        school=None,
    )
    assert pre == {"exact": None, "embedding": None, "chunks": None}
    s = cache.stats()
    assert s["misses"]["exact"] >= 1
    assert s["misses"]["embedding"] >= 1
    assert s["misses"]["chunks"] >= 1
    assert s["errors"] == 0


async def test_set_with_nonpositive_ttl_is_refused():
    from backend.core.cache import _safe_set

    ok = await _safe_set("rag:test:zero-ttl", b"x", 0)
    assert ok is False
