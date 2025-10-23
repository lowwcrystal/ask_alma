from __future__ import annotations
from typing import Dict, List, Callable, Any
import hashlib
import numpy as np
from tqdm import tqdm

# --- Choose your backends here ---
# LangChain embedding classes
from langchain_community.embeddings import OllamaEmbeddings, HuggingFaceEmbeddings
# If you want OpenAI (optional):
try:
    from langchain_openai import OpenAIEmbeddings     # requires OPENAI_API_KEY
except Exception:
    OpenAIEmbeddings = None


# ---------- 1) MODEL REGISTRY / CONFIG ----------
# Each entry defines how to build the LangChain Embeddings object and optional kwargs.
# Enable/disable entries by commenting them in/out inside ENABLED_MODELS.
MODEL_BUILDERS: Dict[str, Callable[[], Any]] = {
    "ollama:nomic-embed-text": lambda: OllamaEmbeddings(
        model="nomic-embed-text", base_url="http://localhost:11434"
    ),

    # Hugging Face local (CPU/GPU). Good default: all-MiniLM-L6-v2 (384-dim)
    "hf:all-MiniLM-L6-v2": lambda: HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        encode_kwargs={"normalize_embeddings": True}
    ),

    # OpenAI (paid / hosted). Uncomment only if you have an API key.
    # "openai:text-embedding-3-small": lambda: OpenAIEmbeddings(
    #     model="text-embedding-3-small"   # 1536 dims
    # ),
}

ENABLED_MODELS: List[str] = [
    "ollama:nomic-embed-text",
    # "hf:all-MiniLM-L6-v2",
    # "openai:text-embedding-3-small",
]


# ---------- 2) UTILITIES ----------
# for each chunk, create a short stable id
def _hash_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# embedding chunks in batches of 64
def _batch(iterable, n=64):
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == n:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


# ---------- 3) CORE FUNCTION ----------
def embed_corpus(
    chunks: List[str],
    models: List[str] = None,
    batch_size: int = 64,
) -> Dict[str, Dict[str, Any]]:
    """
    Returns a dict:
      {
        model_name: {
          "embeddings": np.ndarray [N x D],
          "dim": int,
          "texts": List[str],
          "ids": List[str],  # stable ids per text
        },
        ...
      }
    """
    if models is None:
        models = ENABLED_MODELS

    results: Dict[str, Dict[str, Any]] = {}
    ids = [_hash_text(t) for t in chunks]

    for model_name in models:
        if model_name not in MODEL_BUILDERS:
            raise ValueError(f"Unknown model '{model_name}'. Add it to MODEL_BUILDERS.")

        embedder = MODEL_BUILDERS[model_name]()
        vectors: List[List[float]] = []

        # Try batched embedding (LangChain embeds) with graceful fallback
        try:
            # Some backends support list input natively; we still batch to control memory.
            for batch in tqdm(list(_batch(chunks, batch_size)), desc=f"Embedding [{model_name}]"):
                vectors.extend(embedder.embed_documents(batch))
        except TypeError:
            # Fallback to per-item embedding if the backend doesn't support list calls
            for t in tqdm(chunks, desc=f"Embedding [{model_name}]"):
                vectors.append(embedder.embed_query(t))

        arr = np.array(vectors, dtype="float32")
        results[model_name] = {
            "embeddings": arr,
            "dim": arr.shape[1] if arr.ndim == 2 else len(arr[0]),
            "texts": chunks,
            "ids": ids,
        }

    return results


# ---------- 4) OPTIONAL PERSIST HELPERS ----------
def save_numpy_bundle(result: Dict[str, Dict[str, Any]], out_dir: str = "./emb_out"):
    """
    Saves:
      - {model}.npy: embeddings
      - {model}.meta.tsv: id<TAB>text
    """
    import os
    os.makedirs(out_dir, exist_ok=True)

    for model_name, payload in result.items():
        safe = model_name.replace(":", "_").replace("/", "_")
        npy_path = os.path.join(out_dir, f"{safe}.npy")
        meta_path = os.path.join(out_dir, f"{safe}.meta.tsv")

        np.save(npy_path, payload["embeddings"])
        with open(meta_path, "w", encoding="utf-8") as f:
            for _id, txt in zip(payload["ids"], payload["texts"]):
                f.write(f"{_id}\t{txt.replace('\n',' ')}\n")

        print(f"Saved: {npy_path} ({payload['embeddings'].shape})")
        print(f"Saved: {meta_path}")


# ---------- 5) QUICK DEMO ----------
if __name__ == "__main__":
    chunks = [
        "COMS W3134 covers core data structures like stacks, queues, and BSTs.",
        "Lit Hum explores foundational texts in the Western canon.",
        "Prerequisite for PHYS UN1401 is high school calculus or equivalent.",
    ]

    result = embed_corpus(chunks, models=ENABLED_MODELS, batch_size=64)
    for name, payload in result.items():
        print(name, payload["embeddings"].shape, "dim:", payload["dim"])

    save_numpy_bundle(result, out_dir="./emb_out")