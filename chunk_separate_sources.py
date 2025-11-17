#!/usr/bin/env python3
"""
Chunk seas_2026.jsonl and barnard_2026.jsonl separately
"""

import sys
from pathlib import Path

# Add src/chunking to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "chunking"))

from data_chunking import process_jsonl_files
import json

# Process each file separately
files_to_process = [
    ("seas_2026.jsonl", "chunked_seas_2026.jsonl"),
    ("barnard_2026.jsonl", "chunked_barnard_2026.jsonl")
]

all_chunked_data = []

for input_file, output_file in files_to_process:
    print(f"\nProcessing {input_file}...")
    chunked_data = process_jsonl_files([input_file], max_chars=300)
    
    # Save individual file
    with open(output_file, "w", encoding="utf-8") as f:
        for record in chunked_data:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"✓ Saved {len(chunked_data)} chunks to {output_file}")
    all_chunked_data.extend(chunked_data)

# Also save combined file
print(f"\nSaving combined file...")
with open("chunked_bulletins.jsonl", "w", encoding="utf-8") as f:
    for record in all_chunked_data:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"✓ Saved {len(all_chunked_data)} total unique chunks to chunked_bulletins.jsonl")

