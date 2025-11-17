#!/usr/bin/env python3
"""
Chunk the scraped JSONL files (seas_2026.jsonl, barnard_2026.jsonl)
"""

import sys
from pathlib import Path

# Add src/chunking to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "chunking"))

from data_chunking import process_jsonl_files
import json

# Files to chunk
filenames = [
    "seas_2026.jsonl",
    "barnard_2026.jsonl"
]

print(f"Chunking {len(filenames)} files...")
chunked_data = process_jsonl_files(filenames, max_chars=300)

# Save the chunks to a new JSONL file for embeddings
output_file = "chunked_scraped_2026.jsonl"
with open(output_file, "w", encoding="utf-8") as f:
    for record in chunked_data:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"✓ Saved {len(chunked_data)} chunks to {output_file}")

