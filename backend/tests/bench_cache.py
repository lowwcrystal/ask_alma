

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from typing import Callable, Dict, List

from backend.core import cache


def _pct(samples: List[float], q: float) -> float:
    """Return the qth percentile of `samples` in milliseconds."""
    if not samples:
        return float("nan")
    s = sorted(samples)
    k = int(round(q / 100.0 * (len(s) - 1)))
    return s[k] * 1000


async def _time_call(fn: Callable, iters: int = 20) -> List[float]:
    """Time `fn()` `iters` times. Returns raw per-call seconds."""
    samples = []
    for _ in range(iters):
        t0 = time.perf_counter()
        await fn()
        samples.append(time.perf_counter() - t0)
    return samples


def _print_table(rows: List[Dict[str, str]]) -> None:
    if not rows:
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    sep = " | "
    print(sep.join(c.ljust(widths[c]) for c in cols))
    print("-+-".join("-" * widths[c] for c in cols))
    for r in rows:
        print(sep.join(str(r[c]).ljust(widths[c]) for c in cols))


async def bench_latency(iters: int = 20) -> None:
    assert await cache.ping(), "Redis not reachable; set REDIS_URL first"

    query = "bench latency query — what are CC core classes?"
    chunks = [{"id": i, "content": f"chunk {i}", "similarity": 0.9 - i * 0.01, "source": "cc"} for i in range(6)]
    vector = [0.1] * 1536
    payload = {"answer": "x" * 2000, "matches": chunks}  # realistic ~5KB payload

    # Prime
    await cache.set_embedding(query, vector)
    await cache.set_chunks(query, "columbia_college", chunks)
    await cache.set_exact_response(query, "bench-u", "bench-c", {"school": "columbia_college"}, 0, payload)
    await cache.set_llm_response(query, "bench-u", "bench-c", {"school": "columbia_college"}, 0, chunks, "answer")

    async def l2(): await cache.get_embedding(query)
    async def l3(): await cache.get_chunks(query, "columbia_college")
    async def l1(): await cache.get_exact_response(query, "bench-u", "bench-c", {"school": "columbia_college"}, 0)
    async def l4(): await cache.get_llm_response(query, "bench-u", "bench-c", {"school": "columbia_college"}, 0, chunks)
    async def prefetch():
        await cache.prefetch_layers(
            query=query, user_id="bench-u", conversation_id="bench-c",
            profile={"school": "columbia_college"}, history_len=0, school="columbia_college",
        )

    rows = []
    for name, fn in [("L2 embedding", l2), ("L3 chunks", l3), ("L1 exact", l1), ("L4 llm", l4), ("prefetch (L1+L2+L3)", prefetch)]:
        samples = await _time_call(fn, iters)
        rows.append({
            "layer": name,
            f"P50 (ms)": f"{_pct(samples, 50):.2f}",
            f"P95 (ms)": f"{_pct(samples, 95):.2f}",
            f"max (ms)": f"{max(samples) * 1000:.2f}",
            f"mean (ms)": f"{statistics.mean(samples) * 1000:.2f}",
        })
    _print_table(rows)

    # Cleanup
    client = await cache._get_client()
    if client:
        await client.delete(
            cache.key_embedding(query),
            cache.key_chunks(query, "columbia_college"),
            cache.key_exact(query, "bench-u", "bench-c", {"school": "columbia_college"}, 0),
            cache.key_llm(query, "bench-u", "bench-c", {"school": "columbia_college"}, 0, cache.chunks_fingerprint(chunks)),
        )


# ---------------------------------------------------------------------------
# Bench 2: concurrency / pool saturation
# ---------------------------------------------------------------------------

async def bench_concurrency(concurrency: int = 50) -> None:
    assert await cache.ping(), "Redis not reachable"

    # 1) Same key, many readers — validate pipelining + pool handle it
    query = "bench concurrency same key"
    vector = [0.1] * 1536
    set_ok = await cache.set_embedding(query, vector)
    assert set_ok, f"priming SET failed; stats={cache.stats()}"
    # Verify the key is actually there before fanning out
    primed = await cache.get_embedding(query)
    assert primed == vector, f"priming GET roundtrip failed; got={type(primed).__name__}"

    async def read_one():
        v = await cache.get_embedding(query)
        if v != vector:
            raise AssertionError(
                f"concurrent read mismatch: got type={type(v).__name__} "
                f"len={len(v) if hasattr(v, '__len__') else 'n/a'} "
                f"preview={v[:3] if isinstance(v, list) else v!r}"
            )

    t0 = time.perf_counter()
    await asyncio.gather(*(read_one() for _ in range(concurrency)))
    elapsed = (time.perf_counter() - t0) * 1000
    print(f"same-key concurrent reads: {concurrency} in {elapsed:.1f} ms total "
          f"({elapsed / concurrency:.2f} ms/op)")

    # 2) Distinct keys — verify pool doesn't starve
    async def distinct_read(i: int):
        q = f"bench distinct {i}"
        v = [float(i)] * 16
        await cache.set_embedding(q, v)
        assert await cache.get_embedding(q) == v

    t0 = time.perf_counter()
    await asyncio.gather(*(distinct_read(i) for i in range(concurrency)))
    elapsed = (time.perf_counter() - t0) * 1000
    print(f"distinct-key concurrent set+get: {concurrency} in {elapsed:.1f} ms total")

    s = cache.stats()
    print(f"final stats: hits={s['hits']}  misses={s['misses']}  errors={s['errors']}  circuit_open={s['circuit_open']}")
    assert s["errors"] == 0, "unexpected errors under concurrency"

    # Cleanup
    client = await cache._get_client()
    if client:
        await client.delete(cache.key_embedding(query))
        for i in range(concurrency):
            await client.delete(cache.key_embedding(f"bench distinct {i}"))


# ---------------------------------------------------------------------------
# Bench 3: full-pipeline RAG cold vs warm (requires OpenAI + Postgres)
# ---------------------------------------------------------------------------

async def bench_rag() -> None:
    import os
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("DATABASE_URL"):
        print("SKIP: rag bench needs OPENAI_API_KEY and DATABASE_URL")
        return

    from backend.services.rag_query import rag_answer

    question = "Bench: What are the first year core classes for Columbia College?"
    uid = "bench-user"
    cid = "bench-conv-rag"

    # Cold
    t0 = time.perf_counter()
    cold = await rag_answer(question=question, conversation_id=cid, user_id=uid, save_to_db=False)
    cold_ms = (time.perf_counter() - t0) * 1000

    # Warm
    t0 = time.perf_counter()
    warm = await rag_answer(question=question, conversation_id=cid, user_id=uid, save_to_db=False)
    warm_ms = (time.perf_counter() - t0) * 1000

    print(f"cold: {cold_ms:.0f} ms  ({cold.get('used_model_llm')})")
    print(f"warm: {warm_ms:.0f} ms  ({warm.get('used_model_llm')}  served_from_cache={warm.get('served_from_cache')})")
    print(f"speedup: {cold_ms / warm_ms:.1f}x")
    if warm_ms > cold_ms * 0.2:
        print(f"WARN: warm should be <20% of cold; got {warm_ms / cold_ms * 100:.0f}%")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

async def _main(bench: str, iters: int, concurrency: int) -> int:
    try:
        if bench in ("latency", "all"):
            print("\n=== LATENCY ===")
            await bench_latency(iters=iters)
        if bench in ("concurrency", "all"):
            print("\n=== CONCURRENCY ===")
            await bench_concurrency(concurrency=concurrency)
        if bench in ("rag", "all"):
            print("\n=== FULL RAG ===")
            await bench_rag()
        return 0
    finally:
        await cache.close_cache()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bench", choices=["latency", "concurrency", "rag", "all"])
    parser.add_argument("--iters", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=50)
    args = parser.parse_args()
    sys.exit(asyncio.run(_main(args.bench, args.iters, args.concurrency)))
