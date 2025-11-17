#!/usr/bin/env python3
"""
Convert scraped JSON files (seas_2026.json, barnard_2026.json) to JSONL format
for chunking and embedding.
"""

import json
from tqdm import tqdm

def convert_json_to_jsonl(json_file, jsonl_file, source_name):
    """
    Convert a scraped JSON file to JSONL format.
    
    Args:
        json_file: Path to input JSON file
        jsonl_file: Path to output JSONL file
        source_name: Source identifier (e.g., "seas_2026.json", "barnard_2026.json")
    """
    print(f"Converting {json_file} to {jsonl_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pages = data.get('pages', [])
    print(f"Found {len(pages)} pages")
    
    with open(jsonl_file, 'w', encoding='utf-8') as f:
        for i, page in enumerate(tqdm(pages, desc=f"Writing {jsonl_file}")):
            # Extract full_text from the page
            full_text = page.get('full_text', '').strip()
            
            # Skip pages with no text
            if not full_text:
                continue
            
            # Write as JSONL with page_content field (matching existing format exactly)
            entry = {
                "page_index": i + 1,  # 1-indexed
                "page_content": full_text,
                "source": source_name
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"✓ Converted {len(pages)} pages to {jsonl_file}")

if __name__ == "__main__":
    # Convert SEAS 2026
    convert_json_to_jsonl(
        "seas_2026.json",
        "seas_2026.jsonl",
        "seas_2026.json"
    )
    
    # Convert Barnard 2026
    convert_json_to_jsonl(
        "barnard_2026.json",
        "barnard_2026.jsonl",
        "barnard_2026.json"
    )
    
    print("\n✓ Conversion complete!")

