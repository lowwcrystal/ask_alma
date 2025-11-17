#!/usr/bin/env python3
"""
Comprehensive script to:
1. Convert columbia_college_2026.json to JSONL
2. Chunk all 2024-2025 and 2026 data with overlap and deduplication
3. Generate embeddings
4. Delete all embeddings from Supabase
5. Upload all new embeddings
"""

import json
import os
import sys
from tqdm import tqdm

# Step 1: Convert columbia_college_2026.json to JSONL
print("="*80)
print("Step 1: Converting columbia_college_2026.json to JSONL")
print("="*80)

def convert_json_to_jsonl(json_file, jsonl_file, source_name):
    """Convert a scraped JSON file to JSONL format."""
    print(f"Converting {json_file} to {jsonl_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pages = data.get('pages', [])
    print(f"Found {len(pages)} pages")
    
    with open(jsonl_file, 'w', encoding='utf-8') as f:
        for i, page in enumerate(tqdm(pages, desc=f"Writing {jsonl_file}")):
            full_text = page.get('full_text', '').strip()
            
            if not full_text:
                continue
            
            entry = {
                "page_index": i + 1,
                "page_content": full_text,
                "source": source_name
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"✓ Converted to {jsonl_file}\n")

# Convert columbia_college_2026.json
if os.path.exists("columbia_college_2026.json"):
    convert_json_to_jsonl(
        "columbia_college_2026.json",
        "columbia_college_2026.jsonl",
        "columbia_college_2026.json"
    )
else:
    print("columbia_college_2026.json not found, skipping conversion\n")

# Step 2: Chunk all data
print("="*80)
print("Step 2: Chunking all data with overlap and deduplication")
print("="*80)

# Import chunking functions
sys.path.insert(0, 'src/chunking')
from data_chunking import process_jsonl_files

# All files to process (2024-2025 and 2026)
all_files = [
    # 2024-2025 data
    "barnard_2024_2025.jsonl",
    "columbia_engineering_2024_2025.jsonl",
    "columbia_college_2024_2025.jsonl",
    # 2026 data
    "seas_2026.jsonl",
    "barnard_2026.jsonl",
    "columbia_college_2026.jsonl"
]

# Filter to only existing files
existing_files = [f for f in all_files if os.path.exists(f)]
print(f"Processing {len(existing_files)} files:")
for f in existing_files:
    print(f"  - {f}")

# Process all files with overlap
chunked_data = process_jsonl_files(existing_files, max_chars=300, overlap_chars=50)

# Save all chunks
output_file = "chunked_all_bulletins.jsonl"
with open(output_file, "w", encoding="utf-8") as f:
    for record in chunked_data:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"\n✓ Saved {len(chunked_data)} unique chunks to {output_file}")

print("\n" + "="*80)
print("Next steps:")
print("1. Run embedder.py to generate embeddings")
print("2. Run upload_embeddings.py to delete old and upload new embeddings")
print("="*80)

