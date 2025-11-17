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


# ---------- 3) CHECKPOINT HELPERS ----------
def save_checkpoint(model_name: str, vectors: List[List[float]], processed_count: int, out_dir: str = "./emb_out"):
    """Save checkpoint after each batch to allow resuming."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    safe = model_name.replace(":", "_").replace("/", "_")
    checkpoint_path = os.path.join(out_dir, f"{safe}.checkpoint.npy")
    np.save(checkpoint_path, np.array(vectors, dtype="float32"))
    # Save progress info
    progress_path = os.path.join(out_dir, f"{safe}.progress.txt")
    with open(progress_path, "w") as f:
        f.write(f"{processed_count}\n")


def load_checkpoint(model_name: str, out_dir: str = "./emb_out") -> tuple[np.ndarray, int]:
    """Load checkpoint if it exists, return (embeddings_array, processed_count)."""
    import os
    safe = model_name.replace(":", "_").replace("/", "_")
    checkpoint_path = os.path.join(out_dir, f"{safe}.checkpoint.npy")
    progress_path = os.path.join(out_dir, f"{safe}.progress.txt")
    
    if os.path.exists(checkpoint_path) and os.path.exists(progress_path):
        embeddings = np.load(checkpoint_path)
        with open(progress_path, "r") as f:
            processed_count = int(f.read().strip())
        return embeddings, processed_count
    return None, 0


def clear_checkpoint(model_name: str, out_dir: str = "./emb_out"):
    """Clear checkpoint files after successful completion."""
    import os
    safe = model_name.replace(":", "_").replace("/", "_")
    checkpoint_path = os.path.join(out_dir, f"{safe}.checkpoint.npy")
    progress_path = os.path.join(out_dir, f"{safe}.progress.txt")
    if os.path.exists(checkpoint_path):
        os.remove(checkpoint_path)
    if os.path.exists(progress_path):
        os.remove(progress_path)


# ---------- 3) CORE FUNCTION ----------
def embed_corpus(
    chunks: List[str],
    models: List[str] = None,
    batch_size: int = 64,
    checkpoint_dir: str = "./emb_out",
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
        
        # Try to load checkpoint
        checkpoint_embeddings, processed_count = load_checkpoint(model_name, checkpoint_dir)
        if checkpoint_embeddings is not None:
            vectors = checkpoint_embeddings.tolist()
            tqdm.write(f"Resuming from checkpoint: {processed_count}/{len(chunks)} chunks already processed")
        else:
            vectors = []
            processed_count = 0

        # Try batched embedding (LangChain embeds) with graceful fallback
        try:
            # Some backends support list input natively; we still batch to control memory.
            batches = list(_batch(chunks, batch_size))
            import time
            
            # Skip batches that were already processed
            start_batch = processed_count // batch_size
            batches_to_process = batches[start_batch:]
            
            if start_batch > 0:
                tqdm.write(f"Skipping {start_batch} already-processed batches")
            
            for batch_idx, batch in enumerate(tqdm(batches_to_process, desc=f"Embedding [{model_name}]", unit="batch", 
                            initial=start_batch, total=len(batches),
                            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]')):
                # Retry logic for rate limits
                max_retries = 5
                retry_delay = 2
                for attempt in range(max_retries):
                    try:
                        batch_vectors = embedder.embed_documents(batch)
                        vectors.extend(batch_vectors)
                        processed_count += len(batch)
                        
                        # Save checkpoint after each successful batch
                        save_checkpoint(model_name, vectors, processed_count, checkpoint_dir)
                        break
                    except Exception as e:
                        if "rate_limit" in str(e).lower() or "429" in str(e) or "RateLimitError" in str(type(e).__name__):
                            if attempt < max_retries - 1:
                                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                                tqdm.write(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                                time.sleep(wait_time)
                            else:
                                # Save checkpoint before raising error
                                save_checkpoint(model_name, vectors, processed_count, checkpoint_dir)
                                tqdm.write(f"Saved checkpoint at {processed_count}/{len(chunks)} chunks. Resume by running again.")
                                raise
                        else:
                            raise
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
        
        # Clear checkpoint after successful completion
        clear_checkpoint(model_name, checkpoint_dir)

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
    # Use smaller batch size (32) for larger chunks (2000+ chars) to avoid rate limits
    result = embed_corpus(chunks, models=ENABLED_MODELS, batch_size=32)
    
    for name, payload in result.items():
        print(f"{name}: {payload['embeddings'].shape}, dim: {payload['dim']}")
    
    save_numpy_bundle(result, metadata=metadata, out_dir="./emb_out")