#!/usr/bin/env python3
"""
Update the source column in Supabase for existing embeddings
by matching chunk content from the chunked JSONL file.
"""

import os
import sys
import json
import hashlib
from tqdm import tqdm
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL not set in .env")

# Ensure SSL (Supabase requires it)
if "sslmode=" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

def _hash_text(s: str) -> str:
    """Generate the same hash used by embedder.py"""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

# Connect to database
try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()
    print("Connected to Supabase Postgres.")
except Exception as e:
    sys.exit(f"Failed to connect: {e}")

# Load chunked JSONL file to get source mappings
chunked_file = os.path.join(os.path.dirname(__file__), "..", "..", "chunked_all_bulletins.jsonl")
print(f"Loading source mappings from {chunked_file}...")

id_to_source = {}
with open(chunked_file, "r", encoding="utf-8") as f:
    for line in tqdm(f, desc="Reading chunks"):
        if line.strip():
            data = json.loads(line)
            text = data.get("text", "") or data.get("page_content", "")
            source = data.get("source", "unknown")
            chunk_id = _hash_text(text)
            id_to_source[chunk_id] = source

print(f"Loaded {len(id_to_source)} chunk ID to source mappings\n")

# Update sources in database
print("Updating source column in database...")
updated_count = 0
not_found_count = 0

# Get all rows from database
cur.execute("SELECT id, content FROM documents;")
rows = cur.fetchall()

print(f"Found {len(rows)} rows in database\n")

for row_id, content in tqdm(rows, desc="Updating sources"):
    # Generate the same ID that would be used for this content
    content_id = _hash_text(content)
    
    if content_id in id_to_source:
        source = id_to_source[content_id]
        # Update the source for this row
        cur.execute(
            "UPDATE documents SET source = %s WHERE id = %s",
            (source, row_id)
        )
        updated_count += 1
    else:
        not_found_count += 1

# Commit changes
conn.commit()
print(f"\n✓ Updated {updated_count} rows")
if not_found_count > 0:
    print(f"  {not_found_count} rows not found in chunked file (may have different content)")

cur.close()
conn.close()
print("Connection closed.")

