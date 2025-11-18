#!/usr/bin/env python3
"""
Generate embeddings for CULPA professor reviews and upload to Supabase
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src/embedder to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "embedder"))

from embedder import load_chunks_from_jsonl, embed_corpus, save_numpy_bundle, ENABLED_MODELS

# Load environment variables (OPENAI_API_KEY)
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Error: OPENAI_API_KEY not set in .env file")

# Path to CULPA chunks
jsonl_files = ["chunked_culpa_reviews.jsonl"]

print("=" * 60)
print("CULPA Reviews Embedding Pipeline")
print("=" * 60)

# Load chunks from JSONL file
print("\n[1/3] Loading chunks from JSONL...")
chunks, metadata = load_chunks_from_jsonl(jsonl_files)

if not chunks:
    sys.exit("Error: No chunks loaded. Check the JSONL file.")

print(f"✓ Loaded {len(chunks)} chunks")
print(f"  Sample source: {metadata[0]['source']}")
print(f"  First chunk length: {len(chunks[0])} characters")

# Generate embeddings
print("\n[2/3] Generating embeddings with OpenAI text-embedding-3-small...")
print(f"  Using batch size: 32 (optimized for 2000+ char chunks)")
print(f"  Note: This may take a while and will be checkpointed.")

try:
    result = embed_corpus(chunks, models=ENABLED_MODELS, batch_size=32)
    
    for name, payload in result.items():
        print(f"\n✓ Embeddings generated:")
        print(f"  Model: {name}")
        print(f"  Shape: {payload['embeddings'].shape}")
        print(f"  Dimensions: {payload['dim']}")
except Exception as e:
    print(f"\n✗ Embedding failed: {e}")
    print("\nNote: If rate limited, the progress is saved. Just run this script again to resume.")
    sys.exit(1)

# Save embeddings to files
print("\n[3/3] Saving embeddings to emb_out/...")
save_numpy_bundle(result, metadata=metadata, out_dir="./emb_out")

print("\n" + "=" * 60)
print("✅ Embeddings generated successfully!")
print("=" * 60)
print("\nNext steps:")
print("1. Review the generated files in emb_out/:")
print("   - openai_text-embedding-3-small.npy (embeddings)")
print("   - openai_text-embedding-3-small.meta.tsv (metadata)")
print("\n2. Upload to Supabase by running:")
print("   python3 src/embedder/upload_embeddings.py")
print("\nNote: upload_embeddings.py will DELETE all existing documents")
print("      and replace them with the new embeddings.")
print("=" * 60)

