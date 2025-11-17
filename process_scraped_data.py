#!/usr/bin/env python3
"""
Complete pipeline to process scraped JSON files:
1. Convert JSON to JSONL
2. Chunk the JSONL files
3. Generate embeddings
4. Upload to Supabase
"""

import os
import sys
import subprocess
from pathlib import Path

# Add src directories to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "chunking"))
sys.path.insert(0, str(Path(__file__).parent / "src" / "embedder"))

def run_step(step_name, command, description):
    """Run a step in the pipeline."""
    print(f"\n{'='*80}")
    print(f"Step: {step_name}")
    print(f"Description: {description}")
    print(f"{'='*80}\n")
    
    result = subprocess.run(command, shell=True, cwd=Path(__file__).parent)
    if result.returncode != 0:
        print(f"\n❌ Error in {step_name}")
        sys.exit(1)
    print(f"\n✓ {step_name} completed successfully")

def main():
    # Step 1: Convert JSON to JSONL
    run_step(
        "Convert JSON to JSONL",
        "python3 convert_json_to_jsonl.py",
        "Converting seas_2026.json and barnard_2026.json to JSONL format"
    )
    
    # Step 2: Chunk the JSONL files
    print("\n" + "="*80)
    print("Step: Chunk JSONL files")
    print("Description: Splitting text into chunks for embedding")
    print("="*80 + "\n")
    
    # Import and run chunking
    from data_chunking import process_jsonl_files, sentence_chunk_text
    import json
    from tqdm import tqdm
    
    filenames = ["seas_2026.jsonl", "barnard_2026.jsonl"]
    chunked_data = process_jsonl_files(filenames, max_chars=300)
    
    # Save chunked data
    chunked_file = "chunked_scraped_2026.jsonl"
    with open(chunked_file, "w", encoding="utf-8") as f:
        for record in chunked_data:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"✓ Saved {len(chunked_data)} chunks to {chunked_file}")
    
    # Step 3: Generate embeddings
    print("\n" + "="*80)
    print("Step: Generate embeddings")
    print("Description: Creating embeddings using OpenAI API")
    print("="*80 + "\n")
    
    # Import and run embedder
    from embedder import load_chunks_from_jsonl, embed_corpus, save_numpy_bundle
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Load chunks
    chunks, metadata = load_chunks_from_jsonl([chunked_file])
    
    # Generate embeddings
    print(f"\nEmbedding {len(chunks)} chunks...")
    result = embed_corpus(chunks, models=["text-embedding-3-small"], batch_size=64)
    
    for name, payload in result.items():
        print(f"{name}: {payload['embeddings'].shape}, dim: {payload['dim']}")
    
    # Save embeddings
    save_numpy_bundle(result, out_dir="./emb_out")
    print("✓ Embeddings saved")
    
    # Step 4: Upload to Supabase
    run_step(
        "Upload to Supabase",
        "cd src/embedder && python3 upload_embeddings.py",
        "Uploading embeddings to Supabase database"
    )
    
    print("\n" + "="*80)
    print("✓ Pipeline completed successfully!")
    print("="*80)

if __name__ == "__main__":
    main()

