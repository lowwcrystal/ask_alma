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

    # OpenAI (paid / hosted). Requires OPENAI_API_KEY in environment.
    "openai:text-embedding-3-small": lambda: OpenAIEmbeddings(
        model="text-embedding-3-small"   # 1536 dims
    ),
}

ENABLED_MODELS: List[str] = [
    # "ollama:nomic-embed-text",
    # "hf:all-MiniLM-L6-v2",
    "openai:text-embedding-3-small",
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
            batches = list(_batch(chunks, batch_size))
            for batch in tqdm(batches, desc=f"Embedding [{model_name}]", unit="batch", 
                            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'):
                vectors.extend(embedder.embed_documents(batch))
        except TypeError:
            # Fallback to per-item embedding if the backend doesn't support list calls
            for t in tqdm(chunks, desc=f"Embedding [{model_name}]", unit="chunk",
                         bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'):
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
def save_numpy_bundle(result: Dict[str, Dict[str, Any]], metadata: List[Dict[str, Any]] = None, out_dir: str = "./emb_out"):
    """
    Saves:
      - {model}.npy: embeddings
      - {model}.meta.tsv: id<TAB>text<TAB>source
    """
    import os
    os.makedirs(out_dir, exist_ok=True)

    for model_name, payload in result.items():
        safe = model_name.replace(":", "_").replace("/", "_")
        npy_path = os.path.join(out_dir, f"{safe}.npy")
        meta_path = os.path.join(out_dir, f"{safe}.meta.tsv")

        np.save(npy_path, payload["embeddings"])
        with open(meta_path, "w", encoding="utf-8") as f:
            for i, (_id, txt) in enumerate(zip(payload["ids"], payload["texts"])):
                # Get source from metadata if available
                source = metadata[i].get("source", "unknown") if metadata and i < len(metadata) else "unknown"
                f.write(f"{_id}\t{txt.replace('\n',' ')}\t{source}\n")

        print(f"Saved: {npy_path} ({payload['embeddings'].shape})")
        print(f"Saved: {meta_path}")


# ---------- 5) LOAD CHUNKS FROM JSONL ----------
def load_chunks_from_jsonl(file_paths: List[str]) -> tuple[List[str], List[Dict[str, Any]]]:
    """
    Load chunks from multiple JSONL files and extract page_content field.
    
    Returns:
        chunks: List of page_content strings
        metadata: List of metadata dicts (page_index, source)
    """
    import json
    
    chunks = []
    metadata = []
    
    for file_path in file_paths:
        print(f"Loading chunks from {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    data = json.loads(line)
                    # Support both 'page_content' and 'text' fields
                    text = data.get("page_content") or data.get("text", "")
                    chunks.append(text)
                    metadata.append({
                        "page_index": data.get("page_index", None),
                        "source": data.get("source", "unknown")
                    })
    
    print(f"Loaded {len(chunks)} chunks from {len(file_paths)} files.")
    return chunks, metadata


# ---------- 6) QUICK DEMO ----------
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Load environment variables (OPENAI_API_KEY)
    load_dotenv()
    
    # Path to the JSONL files (relative to embedder.py location)
    # embedder.py is in: src/embedder/embedder.py
    # JSONL files are in the root directory
    base_path = os.path.join(os.path.dirname(__file__), "..", "..")
    
    jsonl_files = [
        os.path.join(base_path, "chunked_all_bulletins.jsonl"),
    ]
    
    # Load chunks from JSONL files
    chunks, metadata = load_chunks_from_jsonl(jsonl_files)
    
    print(f"\nEmbedding {len(chunks)} chunks...")
    result = embed_corpus(chunks, models=ENABLED_MODELS, batch_size=64)
    
    for name, payload in result.items():
        print(f"{name}: {payload['embeddings'].shape}, dim: {payload['dim']}")
    
    save_numpy_bundle(result, metadata=metadata, out_dir="./emb_out")