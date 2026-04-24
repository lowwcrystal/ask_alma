"""
Phase 2 - end-to-end RAG pipeline with the 4-layer cache.

Mocks the expensive boundaries:
  * OpenAIEmbeddings.aembed_query    -> fixed 8-dim vector
  * ChatOpenAI.ainvoke               -> canned response
  * psycopg2 connection              -> in-memory fake
  * conversation + profile helpers   -> no-ops

What this verifies:
  * Cold run populates all populated-on-miss layers (L2, L3, L4, L1).
  * Warm run does NOT call the embedder or the LLM.
  * Different user with same query gets L2/L3 hits but L1/L4 misses.
  * `served_from_cache` is set in the response on L1 hits.

Gated behind `needs_redis` so it skips cleanly without a running Redis.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core import cache
from backend.core.config import settings


def _uniq() -> str:
    """Unique suffix so keys don't leak across test runs against a shared Redis."""
    return uuid.uuid4().hex[:12]


pytestmark = [pytest.mark.asyncio, pytest.mark.needs_redis]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_vector() -> List[float]:
    return [0.1] * 8


@pytest.fixture
def fake_chunks() -> List[Dict[str, Any]]:
    return [
        {"id": 1001, "content": "Columbia Core Curriculum...", "similarity": 0.92, "source": "cc_2026"},
        {"id": 1002, "content": "Literature Humanities is required...", "similarity": 0.88, "source": "cc_2026"},
    ]


@pytest.fixture
def fake_conn():
    """Stand-in psycopg2 connection. Nothing calls through it because
    retrieval + conversation helpers are all patched out."""
    conn = MagicMock()
    conn.close = MagicMock()
    return conn


@pytest.fixture(autouse=True)
def patch_rag_boundaries(fake_vector, fake_chunks, fake_conn):
    """
    Replace every I/O boundary inside rag_query.rag_answer so the test
    doesn't need OpenAI keys, Supabase, or a real pgvector index.
    """
    from backend.services import rag_query

    # Async embedder
    mock_embedder = MagicMock()
    mock_embedder.aembed_query = AsyncMock(return_value=fake_vector)

    # Async chat LLM
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="MOCKED ANSWER"))

    # Sync retrieval (runs in to_thread) returns canned chunks
    def _fake_retrieve(conn, question, q_vec, profile, table_name, probes):
        return fake_chunks

    # DB helpers that would otherwise talk to Postgres
    patches = [
        patch.object(rag_query, "OpenAIEmbeddings", return_value=mock_embedder),
        patch.object(rag_query, "ChatOpenAI", return_value=mock_llm),
        patch.object(rag_query, "_vector_search_sync", side_effect=_fake_retrieve),
        patch.object(rag_query, "get_pg_conn", return_value=fake_conn),
        patch.object(rag_query, "get_user_profile", return_value={"school": "columbia_college"}),
        patch.object(rag_query, "get_conversation_history", return_value=[]),
        patch.object(rag_query, "save_message", return_value=None),
        patch.object(rag_query, "create_conversation", return_value="test-conv-id"),
    ]
    for p in patches:
        p.start()
    yield {
        "embedder": mock_embedder,
        "llm": mock_llm,
    }
    for p in patches:
        p.stop()


@pytest.fixture(autouse=True)
async def _clear_redis_keys_after(fake_vector, fake_chunks):
    """After each test, wipe the keys we might have written."""
    yield
    client = await cache._get_client()
    if client is None:
        return
    # These are the cache keys the pipeline writes for the canonical test fixtures.
    # We can't enumerate every personalized L1/L4 variant, so delete by pattern.
    # Redis supports SCAN safely; don't KEYS * on prod.
    cursor = 0
    while True:
        cursor, batch = await client.scan(cursor=cursor, match="rag:*pytest*", count=200)
        if batch:
            await client.delete(*batch)
        if cursor == 0:
            break


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_cold_run_calls_embedder_and_llm_once(patch_rag_boundaries):
    """Cold cache -> both expensive boundaries are hit exactly once."""
    from backend.services.rag_query import rag_answer

    uniq = _uniq()
    question = f"pytest cold run {uniq} - what are CC core classes?"
    user_id = f"pytest-user-{uniq}"
    conversation_id = f"pytest-conv-{uniq}"

    result = await rag_answer(
        question=question,
        conversation_id=conversation_id,
        user_id=user_id,
        save_to_db=True,
    )

    assert result["answer"] == "MOCKED ANSWER"
    assert result["conversation_id"] == conversation_id
    assert result.get("served_from_cache") is None, "cold run must not report a cache hit"
    assert patch_rag_boundaries["embedder"].aembed_query.await_count == 1
    assert patch_rag_boundaries["llm"].ainvoke.await_count == 1


async def test_warm_run_skips_embedder_and_llm(patch_rag_boundaries):
    """L1 hit on replay -> zero embedder + zero LLM calls."""
    from backend.services.rag_query import rag_answer

    uniq = _uniq()
    question = f"pytest warm run {uniq} - what are CC core classes?"
    user_id = f"pytest-user-{uniq}"
    conversation_id = f"pytest-conv-{uniq}"

    # Prime the cache
    await rag_answer(question=question, conversation_id=conversation_id, user_id=user_id, save_to_db=True)
    patch_rag_boundaries["embedder"].aembed_query.reset_mock()
    patch_rag_boundaries["llm"].ainvoke.reset_mock()

    # Replay — everything should come from L1
    result = await rag_answer(question=question, conversation_id=conversation_id, user_id=user_id, save_to_db=True)

    assert result["answer"] == "MOCKED ANSWER"
    assert result["served_from_cache"] == "exact"
    assert patch_rag_boundaries["embedder"].aembed_query.await_count == 0, "L1 hit must skip embedding"
    assert patch_rag_boundaries["llm"].ainvoke.await_count == 0, "L1 hit must skip LLM"


async def test_different_user_same_question_reuses_l2_l3(patch_rag_boundaries):
    """Second user with identical query should hit L2+L3 but miss L1+L4."""
    from backend.services.rag_query import rag_answer

    uniq = _uniq()
    question = f"pytest shared query {uniq} - what is Lit Hum?"
    # First user primes L2/L3 (and its own L1/L4)
    await rag_answer(question=question, conversation_id=f"conv-A-{uniq}", user_id=f"user-A-{uniq}", save_to_db=True)
    patch_rag_boundaries["embedder"].aembed_query.reset_mock()
    patch_rag_boundaries["llm"].ainvoke.reset_mock()

    # Second user — same query, different identity
    result = await rag_answer(question=question, conversation_id=f"conv-B-{uniq}", user_id=f"user-B-{uniq}", save_to_db=True)

    assert result["answer"] == "MOCKED ANSWER"
    # L1 keyed on user -> miss -> full pipeline rerun, BUT
    # L2 (embedding) should still hit cache -> no embedder call.
    # L3 (chunks) should hit cache -> no new retrieval (verified via metrics).
    assert patch_rag_boundaries["embedder"].aembed_query.await_count == 0, \
        "L2 cache hit should prevent re-embedding"
    # L4 is keyed on user+profile so it misses -> LLM IS called (once).
    assert patch_rag_boundaries["llm"].ainvoke.await_count == 1, \
        "different user => L4 miss => LLM gets called"

    # And metrics show the right mix
    s = cache.stats()
    assert s["hits"]["embedding"] >= 1
    assert s["hits"]["chunks"] >= 1
    assert s["misses"]["exact"] >= 1
    assert s["misses"]["llm"] >= 1


async def test_cache_metrics_report_without_errors(patch_rag_boundaries):
    """Metrics endpoint should never show errors on happy-path traffic."""
    from backend.services.rag_query import rag_answer

    uniq = _uniq()
    await rag_answer(
        question=f"pytest metrics check {uniq}",
        conversation_id=f"conv-M-{uniq}", user_id=f"user-M-{uniq}",
        save_to_db=True,
    )
    s = cache.stats()
    assert s["errors"] == 0, f"unexpected cache errors: {s}"
    assert s["enabled"] is True
    assert s["circuit_open"] is False


@pytest.mark.needs_redisearch
async def test_paraphrase_hits_semantic_cache(patch_rag_boundaries, monkeypatch):
    """Two different queries sharing an embedding hit L1.5 without an LLM call.

    Uses a fresh conversation (history_len == 0) so the semantic layer is
    eligible on both the write and the read paths.
    """
    from backend.services.rag_query import rag_answer

    monkeypatch.setattr(settings, "SEMANTIC_CACHE_ENABLED", True)
    monkeypatch.setattr(settings, "SEMANTIC_CACHE_SHADOW_MODE", False)
    monkeypatch.setattr(settings, "SEMANTIC_EMBED_DIM", 8)
    cache._reset_semantic_state()

    uniq = _uniq()
    shared_vec = [0.1] * 8
    patch_rag_boundaries["embedder"].aembed_query = AsyncMock(return_value=shared_vec)

    await rag_answer(
        question=f"primary question {uniq} - what are the CC core classes?",
        conversation_id=None,
        user_id=f"user-primary-{uniq}",
        save_to_db=False,
    )
    patch_rag_boundaries["llm"].ainvoke.reset_mock()

    result = await rag_answer(
        question=f"paraphrase {uniq} - list the Columbia College required courses",
        conversation_id=None,
        user_id=f"user-paraphrase-{uniq}",
        save_to_db=False,
    )

    assert result["answer"] == "MOCKED ANSWER"
    assert result["served_from_cache"] == "semantic"
    assert patch_rag_boundaries["llm"].ainvoke.await_count == 0, \
        "semantic hit must short-circuit the LLM"
    assert cache.stats()["hits"]["semantic"] >= 1
