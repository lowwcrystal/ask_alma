#!/usr/bin/env python3
"""
Generate embeddings for chunked scraped data
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add src/embedder to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "embedder"))

from embedder import load_chunks_from_jsonl, embed_corpus, save_numpy_bundle

# Load environment variables
load_dotenv()

# Load chunks from the chunked file
chunked_file = "chunked_scraped_2026.jsonl"
print(f"Loading chunks from {chunked_file}...")
chunks, metadata = load_chunks_from_jsonl([chunked_file])

print(f"\nEmbedding {len(chunks)} chunks...")
print("This may take a while and will use OpenAI API credits...")

# Generate embeddings
result = embed_corpus(chunks, models=["text-embedding-3-small"], batch_size=64)

for name, payload in result.items():
    print(f"{name}: {payload['embeddings'].shape}, dim: {payload['dim']}")

# Save embeddings (to project root emb_out directory)
project_root = Path(__file__).parent
emb_out_dir = project_root / "emb_out"
emb_out_dir.mkdir(exist_ok=True)

print(f"\nSaving embeddings to {emb_out_dir}...")
save_numpy_bundle(result, out_dir=str(emb_out_dir))
print("✓ Embeddings saved successfully!")


