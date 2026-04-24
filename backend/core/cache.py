from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import string
import struct
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import orjson

from backend.core.config import settings

logger = logging.getLogger("backend.cache")



_PUNCT_RE = re.compile(f"[{re.escape(string.punctuation)}]")
_WS_RE = re.compile(r"\s+")


def normalize_query(q: str) -> str:
    """Normalize a user query for cache-key purposes.

    Steps: strip → lowercase → strip punctuation → collapse whitespace.
    """
    if not q:
        return ""
    q = q.strip().lower()
    q = _PUNCT_RE.sub(" ", q)
    q = _WS_RE.sub(" ", q).strip()
    return q


def _sha256(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x1f")  
    return h.hexdigest()


def query_fingerprint(query: str) -> str:
    """Stable sha256 hex digest of the normalized query. Used by L2."""
    return _sha256(normalize_query(query))


def personalized_key_parts(
    query: str,
    user_id: Optional[str],
    conversation_id: Optional[str],
    profile: Optional[Dict[str, Any]],
    history_len: int = 0,
) -> str:
    """Compose a deterministic hash for personalized layers (L1, L4).

    Collision-resistant across different users / conversations / profiles.
    """
    profile_sig = ""
    if profile:
        # Only fields that affect prompt / retrieval behavior.
        profile_sig = "|".join(
            str(profile.get(k, "")) for k in (
                "school",
                "academic_year",
                "major",
            )
        )
        minors = profile.get("minors") or []
        classes = profile.get("classes_taken") or []
        if isinstance(minors, (list, tuple)):
            profile_sig += "|" + ",".join(sorted(str(x) for x in minors))
        if isinstance(classes, (list, tuple)):
            profile_sig += "|" + ",".join(sorted(str(x) for x in classes))

    return _sha256(
        normalize_query(query),
        user_id or "anon",
        conversation_id or "none",
        profile_sig,
        str(history_len),
    )


def key_chunks(query: str, school: Optional[str]) -> str:
    """L3 key: depends on query + school filter (vector search is scoped)."""
    return f"rag:chunks:{_sha256(normalize_query(query), school or 'none')}"


def key_embedding(query: str) -> str:
    """L2 key: pure function of the normalized query."""
    return f"rag:embedding:{query_fingerprint(query)}"


def key_exact(
    query: str,
    user_id: Optional[str],
    conversation_id: Optional[str],
    profile: Optional[Dict[str, Any]],
    history_len: int,
) -> str:
    """L1 key: includes user/profile/history so A's answers never leak to B."""
    return f"rag:exact:{personalized_key_parts(query, user_id, conversation_id, profile, history_len)}"


def key_llm(
    query: str,
    user_id: Optional[str],
    conversation_id: Optional[str],
    profile: Optional[Dict[str, Any]],
    history_len: int,
    chunks_fingerprint: str,
) -> str:
    """L4 key: personalized + chunks content. A new retrieval ⇒ a new key."""
    composite = _sha256(
        personalized_key_parts(query, user_id, conversation_id, profile, history_len),
        chunks_fingerprint,
    )
    return f"rag:llm:{composite}"


def chunks_fingerprint(chunks: List[Dict[str, Any]]) -> str:
    """Fingerprint a retrieval result so L4 is invalidated when chunks change."""
    ids = "|".join(str(c.get("id", "")) for c in chunks)
    return _sha256(ids)


# ------------------------------------------------------------------------------
# Metrics
# ------------------------------------------------------------------------------

@dataclass
class CacheMetrics:
    hits: Dict[str, int] = field(default_factory=lambda: {
        "exact": 0, "embedding": 0, "chunks": 0, "llm": 0, "semantic": 0,
    })
    misses: Dict[str, int] = field(default_factory=lambda: {
        "exact": 0, "embedding": 0, "chunks": 0, "llm": 0, "semantic": 0,
    })
    errors: int = 0
    semantic_shadow_hits: int = 0
    semantic_near_misses: int = 0

    @property
    def total_lookups(self) -> int:
        return sum(self.hits.values()) + sum(self.misses.values())

    @property
    def hit_rate(self) -> float:
        lookups = self.total_lookups
        if lookups == 0:
            return 0.0
        return sum(self.hits.values()) / lookups

    def snapshot(self) -> Dict[str, Any]:
        return {
            "hits": dict(self.hits),
            "misses": dict(self.misses),
            "errors": self.errors,
            "semantic_shadow_hits": self.semantic_shadow_hits,
            "semantic_near_misses": self.semantic_near_misses,
            "total_lookups": self.total_lookups,
            "hit_rate": round(self.hit_rate, 4),
        }


metrics = CacheMetrics()


def _record_hit(layer: str) -> None:
    metrics.hits[layer] = metrics.hits.get(layer, 0) + 1
    _maybe_alert_on_hit_rate()


def _record_miss(layer: str) -> None:
    metrics.misses[layer] = metrics.misses.get(layer, 0) + 1
    _maybe_alert_on_hit_rate()


def _maybe_alert_on_hit_rate() -> None:
    lookups = metrics.total_lookups
    every = max(1, settings.CACHE_METRICS_SAMPLE_EVERY)
    if lookups == 0 or lookups % every != 0:
        return
    rate = metrics.hit_rate
    if rate < settings.CACHE_HIT_RATE_ALERT_THRESHOLD:
        logger.warning(
            "cache hit rate degraded: %.2f%% over %d lookups (threshold %.0f%%)",
            rate * 100,
            lookups,
            settings.CACHE_HIT_RATE_ALERT_THRESHOLD * 100,
        )


# ------------------------------------------------------------------------------
# Circuit breaker
# ------------------------------------------------------------------------------

@dataclass
class _CircuitState:
    failure_times: List[float] = field(default_factory=list)
    opened_at: Optional[float] = None

    def record_failure(self) -> None:
        now = time.monotonic()
        self.failure_times.append(now)
        cutoff = now - settings.CIRCUIT_BREAKER_WINDOW_SECONDS
        self.failure_times = [t for t in self.failure_times if t >= cutoff]
        if len(self.failure_times) >= settings.CIRCUIT_BREAKER_FAILURES:
            if self.opened_at is None:
                logger.warning(
                    "cache circuit breaker tripped after %d failures in %ds — "
                    "disabling cache for %ds",
                    len(self.failure_times),
                    settings.CIRCUIT_BREAKER_WINDOW_SECONDS,
                    settings.CIRCUIT_BREAKER_COOLDOWN_SECONDS,
                )
            self.opened_at = now
            self.failure_times.clear()

    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if time.monotonic() - self.opened_at >= settings.CIRCUIT_BREAKER_COOLDOWN_SECONDS:
            logger.info("cache circuit breaker cooldown elapsed — re-enabling")
            self.opened_at = None
            return False
        return True


_circuit = _CircuitState()


# ------------------------------------------------------------------------------
# Connection
# ------------------------------------------------------------------------------

_redis_client: Optional[Any] = None
_redis_init_lock = asyncio.Lock()


async def _get_client() -> Optional[Any]:
    """Return a pooled async Redis client, or None if unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not settings.REDIS_URL:
        return None
    async with _redis_init_lock:
        if _redis_client is not None:
            return _redis_client
        try:
            import redis.asyncio as aioredis
            from redis.asyncio.connection import BlockingConnectionPool

            # BlockingConnectionPool makes callers *wait* for a free connection
            # instead of raising ConnectionError once max_connections is hit.
            # That gives us predictable queueing behavior under bursts while
            # still bounding the socket count at REDIS_MAX_CONNECTIONS.
            pool = BlockingConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=False,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                timeout=settings.REDIS_POOL_WAIT_TIMEOUT,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            )
            _redis_client = aioredis.Redis(connection_pool=pool)
            # Best-effort: request allkeys-lru. Many managed Redis providers
            # (incl. Redis Cloud) forbid CONFIG SET; we ignore the error.
            try:
                await _redis_client.config_set("maxmemory-policy", "allkeys-lru")
            except Exception as e:  # noqa: BLE001
                logger.info("skipping CONFIG SET maxmemory-policy (%s)", e)
            logger.info("redis cache client initialized")
            return _redis_client
        except Exception as e:  # noqa: BLE001
            logger.warning("failed to initialize redis client: %s", e)
            _redis_client = None
            return None


async def close_cache() -> None:
    """Shut down the pool on app teardown."""
    global _redis_client
    if _redis_client is None:
        return
    try:
        await _redis_client.aclose()
    except Exception:  # noqa: BLE001
        pass
    _redis_client = None


async def ping() -> bool:
    client = await _get_client()
    if client is None:
        return False
    try:
        return bool(await client.ping())
    except Exception as e:  
        logger.warning("redis ping failed: %s", e)
        return False


def cache_enabled() -> bool:
    return bool(settings.REDIS_URL) and not _circuit.is_open()


# ------------------------------------------------------------------------------
# Low-level safe get/set
# ------------------------------------------------------------------------------

async def _safe_get(key: str) -> Optional[bytes]:
    if not cache_enabled():
        return None
    client = await _get_client()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception as e:  # noqa: BLE001
        logger.warning("cache GET failed for %s: %s", key, e)
        metrics.errors += 1
        _circuit.record_failure()
        return None


async def _safe_mget(keys: List[str]) -> List[Optional[bytes]]:
    """Pipelined multi-get. Returns same-length list of bytes|None."""
    if not keys or not cache_enabled():
        return [None] * len(keys)
    client = await _get_client()
    if client is None:
        return [None] * len(keys)
    try:
        async with client.pipeline(transaction=False) as pipe:
            for k in keys:
                pipe.get(k)
            values = await pipe.execute()
        return values  # type: ignore[return-value]
    except Exception as e:  # noqa: BLE001
        logger.warning("cache MGET failed (%d keys): %s", len(keys), e)
        metrics.errors += 1
        _circuit.record_failure()
        return [None] * len(keys)


async def _safe_set(key: str, value: bytes, ttl: int) -> bool:
    if not cache_enabled():
        return False
    if ttl <= 0:
        logger.warning("refusing to SET %s without a positive TTL", key)
        return False
    client = await _get_client()
    if client is None:
        return False
    try:
        await client.set(key, value, ex=ttl)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("cache SET failed for %s: %s", key, e)
        metrics.errors += 1
        _circuit.record_failure()
        return False


async def _safe_mset(items: Iterable[Tuple[str, bytes, int]]) -> int:
    """Pipelined multi-set with per-key TTLs. Returns count written."""
    items = list(items)
    if not items or not cache_enabled():
        return 0
    client = await _get_client()
    if client is None:
        return 0
    try:
        async with client.pipeline(transaction=False) as pipe:
            for k, v, ttl in items:
                if ttl <= 0:
                    continue
                pipe.set(k, v, ex=ttl)
            await pipe.execute()
        return len(items)
    except Exception as e:  # noqa: BLE001
        logger.warning("cache MSET failed (%d items): %s", len(items), e)
        metrics.errors += 1
        _circuit.record_failure()
        return 0


# ------------------------------------------------------------------------------
# Serialization
# ------------------------------------------------------------------------------

def _dumps(obj: Any) -> bytes:
    return orjson.dumps(obj, option=orjson.OPT_SERIALIZE_NUMPY)


def _loads(raw: Optional[bytes]) -> Any:
    if raw is None:
        return None
    try:
        return orjson.loads(raw)
    except Exception as e:  # noqa: BLE001
        logger.warning("cache payload decode failed: %s", e)
        return None


# ------------------------------------------------------------------------------
# Public per-layer API
# ------------------------------------------------------------------------------

# L1 — Exact response (short-circuit everything)
async def get_exact_response(
    query: str,
    user_id: Optional[str],
    conversation_id: Optional[str],
    profile: Optional[Dict[str, Any]],
    history_len: int,
) -> Optional[Dict[str, Any]]:
    raw = await _safe_get(key_exact(query, user_id, conversation_id, profile, history_len))
    value = _loads(raw)
    if value is None:
        _record_miss("exact")
        return None
    _record_hit("exact")
    return value


async def set_exact_response(
    query: str,
    user_id: Optional[str],
    conversation_id: Optional[str],
    profile: Optional[Dict[str, Any]],
    history_len: int,
    payload: Dict[str, Any],
) -> bool:
    return await _safe_set(
        key_exact(query, user_id, conversation_id, profile, history_len),
        _dumps(payload),
        settings.CACHE_TTL_EXACT,
    )


# L2 — Query embedding
async def get_embedding(query: str) -> Optional[List[float]]:
    raw = await _safe_get(key_embedding(query))
    value = _loads(raw)
    if value is None:
        _record_miss("embedding")
        return None
    _record_hit("embedding")
    return value


async def set_embedding(query: str, vector: List[float]) -> bool:
    return await _safe_set(
        key_embedding(query),
        _dumps(vector),
        settings.CACHE_TTL_EMBEDDING,
    )


# L3 — Retrieved chunks
async def get_chunks(query: str, school: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    raw = await _safe_get(key_chunks(query, school))
    value = _loads(raw)
    if value is None:
        _record_miss("chunks")
        return None
    _record_hit("chunks")
    return value


async def set_chunks(
    query: str,
    school: Optional[str],
    chunks: List[Dict[str, Any]],
) -> bool:
    return await _safe_set(
        key_chunks(query, school),
        _dumps(chunks),
        settings.CACHE_TTL_CHUNKS,
    )


# L4 — LLM response
async def get_llm_response(
    query: str,
    user_id: Optional[str],
    conversation_id: Optional[str],
    profile: Optional[Dict[str, Any]],
    history_len: int,
    chunks: List[Dict[str, Any]],
) -> Optional[str]:
    raw = await _safe_get(key_llm(
        query, user_id, conversation_id, profile, history_len, chunks_fingerprint(chunks),
    ))
    value = _loads(raw)
    if value is None:
        _record_miss("llm")
        return None
    _record_hit("llm")
    return value


async def set_llm_response(
    query: str,
    user_id: Optional[str],
    conversation_id: Optional[str],
    profile: Optional[Dict[str, Any]],
    history_len: int,
    chunks: List[Dict[str, Any]],
    answer: str,
) -> bool:
    return await _safe_set(
        key_llm(query, user_id, conversation_id, profile, history_len, chunks_fingerprint(chunks)),
        _dumps(answer),
        settings.CACHE_TTL_LLM,
    )


# ------------------------------------------------------------------------------
# Batched pre-fetch (used at the top of rag_answer_async)
# ------------------------------------------------------------------------------

async def prefetch_layers(
    *,
    query: str,
    user_id: Optional[str],
    conversation_id: Optional[str],
    profile: Optional[Dict[str, Any]],
    history_len: int,
    school: Optional[str],
) -> Dict[str, Any]:
    """Single-pipeline lookup of L1/L2/L3.

    L4 can't be prefetched here — it depends on the chunks_fingerprint which
    isn't known until after L3 is resolved / retrieval is done.

    Returns a dict with keys: 'exact', 'embedding', 'chunks'. Values are the
    cached payloads if present, else None. Hit/miss counters are updated.
    """
    keys = [
        key_exact(query, user_id, conversation_id, profile, history_len),
        key_embedding(query),
        key_chunks(query, school),
    ]
    raws = await _safe_mget(keys)
    result: Dict[str, Any] = {"exact": None, "embedding": None, "chunks": None}
    labels = ("exact", "embedding", "chunks")
    for label, raw in zip(labels, raws):
        value = _loads(raw)
        if value is None:
            _record_miss(label)
        else:
            _record_hit(label)
            result[label] = value
    return result


# ------------------------------------------------------------------------------
# Introspection (for /api/cache/stats and tests)
# ------------------------------------------------------------------------------

def stats() -> Dict[str, Any]:
    return {
        **metrics.snapshot(),
        "enabled": cache_enabled(),
        "circuit_open": _circuit.is_open(),
        "redis_configured": bool(settings.REDIS_URL),
    }


def reset_metrics() -> None:
    """For tests / operational reset."""
    for k in metrics.hits:
        metrics.hits[k] = 0
    for k in metrics.misses:
        metrics.misses[k] = 0
    metrics.errors = 0
    metrics.semantic_shadow_hits = 0
    metrics.semantic_near_misses = 0


# ------------------------------------------------------------------------------
# Semantic response cache (L1.5) -- RediSearch HNSW index over query embeddings
# ------------------------------------------------------------------------------

_SEM_INDEX = "rag_qcache_idx"
_SEM_PREFIX = "qcache:"
_SEM_ANSWER_PREFIX = "rag:sem_answer:"

_semantic_available: Optional[bool] = None
_semantic_ready_lock = asyncio.Lock()
_semantic_cap_cache: Dict[str, Any] = {"ok": True, "checked_at": 0.0}


def _cacheable_profile_hash(profile: Optional[Dict[str, Any]]) -> str:
    """Hash of the profile dimensions that actually affect the answer."""
    if not profile:
        return "none"
    school = str(profile.get("school") or "")
    academic_year = str(profile.get("academic_year") or "")
    return hashlib.sha256(f"{school}|{academic_year}".encode("utf-8")).hexdigest()[:16]


def _vec_to_bytes(vec: List[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


async def _probe_redisearch(client: Any) -> bool:
    try:
        modules = await client.execute_command("MODULE", "LIST")
    except Exception:  # noqa: BLE001
        return False
    for entry in modules or []:
        if isinstance(entry, (list, tuple)):
            for item in entry:
                if isinstance(item, (bytes, bytearray)) and item.lower() == b"search":
                    return True
                if isinstance(item, str) and item.lower() == "search":
                    return True
    return False


async def _ensure_semantic_index(client: Any) -> None:
    try:
        await client.execute_command(
            "FT.CREATE", _SEM_INDEX,
            "ON", "HASH",
            "PREFIX", "1", _SEM_PREFIX,
            "SCHEMA",
            "school", "TAG",
            "profile_hash", "TAG",
            "embedding", "VECTOR", "HNSW", "6",
            "TYPE", "FLOAT32",
            "DIM", str(settings.SEMANTIC_EMBED_DIM),
            "DISTANCE_METRIC", "COSINE",
        )
    except Exception as e:  # noqa: BLE001
        if "already exists" in str(e).lower():
            return
        raise


async def semantic_cache_ready() -> bool:
    """Return True when RediSearch is available and the index is bootstrapped."""
    global _semantic_available
    if not settings.SEMANTIC_CACHE_ENABLED:
        return False
    if _semantic_available is not None:
        return _semantic_available
    client = await _get_client()
    if client is None:
        _semantic_available = False
        return False
    async with _semantic_ready_lock:
        if _semantic_available is not None:
            return _semantic_available
        if not await _probe_redisearch(client):
            logger.info("RediSearch module not present; semantic cache disabled")
            _semantic_available = False
            return False
        try:
            await _ensure_semantic_index(client)
            _semantic_available = True
        except Exception as e:  # noqa: BLE001
            logger.warning("semantic index bootstrap failed: %s", e)
            _semantic_available = False
        return _semantic_available


def _reset_semantic_state() -> None:
    """For tests. Forces the next call to re-probe and re-bootstrap."""
    global _semantic_available
    _semantic_available = None
    _semantic_cap_cache["ok"] = True
    _semantic_cap_cache["checked_at"] = 0.0


def _parse_ft_search(raw: Any) -> Optional[Tuple[str, Dict[str, str]]]:
    if not isinstance(raw, (list, tuple)) or len(raw) < 3:
        return None
    count = raw[0]
    if isinstance(count, (bytes, bytearray)):
        try:
            count = int(count)
        except Exception:  # noqa: BLE001
            count = 0
    if not count:
        return None
    doc_id = raw[1]
    if isinstance(doc_id, (bytes, bytearray)):
        doc_id = doc_id.decode("utf-8", errors="replace")
    fields_arr = raw[2]
    if not isinstance(fields_arr, (list, tuple)):
        return None
    fields: Dict[str, str] = {}
    for i in range(0, len(fields_arr) - 1, 2):
        k = fields_arr[i]
        v = fields_arr[i + 1]
        if isinstance(k, (bytes, bytearray)):
            k = k.decode("utf-8", errors="replace")
        if isinstance(v, (bytes, bytearray)):
            try:
                v = v.decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                v = ""
        fields[str(k)] = v if isinstance(v, str) else str(v)
    return str(doc_id), fields


def _ft_info_to_dict(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, (list, tuple)):
        return {}
    out: Dict[str, str] = {}
    for i in range(0, len(raw) - 1, 2):
        k = raw[i]
        v = raw[i + 1]
        if isinstance(k, (bytes, bytearray)):
            k = k.decode("utf-8", errors="replace")
        if isinstance(v, (bytes, bytearray)):
            v = v.decode("utf-8", errors="replace")
        elif isinstance(v, (list, tuple)):
            v = repr(v)
        out[str(k)] = str(v)
    return out


async def _semantic_below_cap(client: Any) -> bool:
    now = time.monotonic()
    if now - float(_semantic_cap_cache["checked_at"]) < 30.0:
        return bool(_semantic_cap_cache["ok"])
    ok = True
    try:
        raw = await client.execute_command("FT.INFO", _SEM_INDEX)
        info = _ft_info_to_dict(raw)
        num_docs = int(info.get("num_docs", "0") or "0")
        ok = num_docs < settings.SEMANTIC_MAX_ENTRIES
    except Exception:  # noqa: BLE001
        ok = True
    _semantic_cap_cache["ok"] = ok
    _semantic_cap_cache["checked_at"] = now
    return ok


async def get_semantic_response(
    *,
    query: str,
    embedding: List[float],
    school: Optional[str],
    profile: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """L1.5 lookup. Returns a cached answer payload if a near-enough prior
    query exists for the same (school, profile_hash); otherwise None.

    Shadow mode logs what would have hit but never returns a payload."""
    if not cache_enabled() or not settings.SEMANTIC_CACHE_ENABLED:
        return None
    if not await semantic_cache_ready():
        return None
    if not embedding:
        return None

    client = await _get_client()
    if client is None:
        return None

    school_tag = school or "none"
    profile_hash = _cacheable_profile_hash(profile)
    vec_bytes = _vec_to_bytes(embedding)

    try:
        search_query = (
            f"(@school:{{{school_tag}}} @profile_hash:{{{profile_hash}}})"
            "=>[KNN 1 @embedding $vec AS score]"
        )
        raw = await client.execute_command(
            "FT.SEARCH", _SEM_INDEX, search_query,
            "PARAMS", "2", "vec", vec_bytes,
            "RETURN", "3", "answer_key", "query_text", "score",
            "SORTBY", "score",
            "DIALECT", "2",
            "LIMIT", "0", "1",
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("semantic cache FT.SEARCH failed: %s", e)
        metrics.errors += 1
        _circuit.record_failure()
        _record_miss("semantic")
        return None

    parsed = _parse_ft_search(raw)
    if parsed is None:
        _record_miss("semantic")
        return None

    _, fields = parsed
    try:
        distance = float(fields.get("score", "2.0"))
    except ValueError:
        distance = 2.0
    similarity = 1.0 - distance
    answer_key = fields.get("answer_key") or ""
    matched_query = fields.get("query_text", "")

    if similarity >= settings.SEMANTIC_THRESHOLD and answer_key:
        raw_blob = await _safe_get(answer_key)
        payload = _loads(raw_blob)
        if payload is None:
            _record_miss("semantic")
            return None

        if settings.SEMANTIC_CACHE_SHADOW_MODE:
            logger.info(
                "semantic shadow hit: score=%.3f school=%s q=%r matched=%r",
                similarity, school, query, matched_query,
            )
            metrics.semantic_shadow_hits += 1
            _record_miss("semantic")
            return None

        logger.info(
            "semantic cache hit: score=%.3f school=%s q=%r matched=%r",
            similarity, school, query, matched_query,
        )
        _record_hit("semantic")
        if isinstance(payload, dict):
            payload["_matched_query"] = matched_query
            payload["_similarity"] = round(similarity, 4)
        return payload

    if similarity >= settings.SEMANTIC_THRESHOLD_WARN:
        metrics.semantic_near_misses += 1
        logger.info(
            "semantic near-miss: score=%.3f (threshold %.3f) q=%r matched=%r",
            similarity, settings.SEMANTIC_THRESHOLD, query, matched_query,
        )
    _record_miss("semantic")
    return None


async def set_semantic_response(
    *,
    query: str,
    embedding: List[float],
    answer: Dict[str, Any],
    school: Optional[str],
    profile: Optional[Dict[str, Any]],
) -> bool:
    """Write a query->answer mapping into the semantic cache. No-op when the
    feature is disabled, RediSearch is absent, or the index is at capacity."""
    if not cache_enabled() or not settings.SEMANTIC_CACHE_ENABLED:
        return False
    if not await semantic_cache_ready():
        return False
    if not embedding or not isinstance(answer, dict):
        return False

    payload_bytes = _dumps(answer)
    if len(payload_bytes) > settings.SEMANTIC_MAX_ANSWER_BYTES:
        return False

    client = await _get_client()
    if client is None:
        return False

    if not await _semantic_below_cap(client):
        return False

    uid = uuid.uuid4().hex
    answer_key = f"{_SEM_ANSWER_PREFIX}{uid}"
    entry_key = f"{_SEM_PREFIX}{uid}"
    school_tag = school or "none"
    profile_hash = _cacheable_profile_hash(profile)
    vec_bytes = _vec_to_bytes(embedding)

    try:
        async with client.pipeline(transaction=False) as pipe:
            pipe.set(answer_key, payload_bytes, ex=settings.CACHE_TTL_SEMANTIC)
            pipe.hset(entry_key, mapping={
                "school": school_tag,
                "profile_hash": profile_hash,
                "embedding": vec_bytes,
                "answer_key": answer_key,
                "query_text": query[:500],
                "created_at": str(int(time.time())),
            })
            pipe.expire(entry_key, settings.CACHE_TTL_SEMANTIC)
            await pipe.execute()
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("semantic cache write failed: %s", e)
        metrics.errors += 1
        _circuit.record_failure()
        return False
