#!/usr/bin/env python3
"""
Upload CULPA embeddings to Supabase WITHOUT deleting existing documents.
This script APPENDS new CULPA chunks to the existing documents table.
"""

import os
import sys
import numpy as np
from tqdm import tqdm
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

# ------------------------
# Config & helpers
# ------------------------
EMB_PATH = "emb_out/openai_text-embedding-3-small.npy"
META_PATH = "emb_out/openai_text-embedding-3-small.meta.tsv"
TABLE_NAME = "documents"

def to_vector_literal(vec: np.ndarray) -> str:
    """
    Convert a 1D numpy array to pgvector literal: [v1,v2,...]
    """
    return "[" + ",".join(f"{float(x):.8f}" for x in vec.tolist()) + "]"

# ------------------------
# Load env & connect
# ------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL not set in .env")

# Ensure SSL (Supabase requires it)
if "sslmode=" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    print("✓ Connected to Supabase Postgres.")
except Exception as e:
    sys.exit(f"Failed to connect: {e}")

# ------------------------
# Check existing documents
# ------------------------
try:
    cur.execute(f"select count(*) from {TABLE_NAME};")
    existing_count = cur.fetchone()[0]
    print(f"✓ Current documents in database: {existing_count}")
    
    # Count CULPA documents
    cur.execute(f"select count(*) from {TABLE_NAME} where source like 'culpa.info%';")
    culpa_count = cur.fetchone()[0]
    print(f"✓ Current CULPA documents: {culpa_count}")
except Exception as e:
    sys.exit(f"Failed to check existing documents: {e}")

# ------------------------
# Ensure extension/table/index
# ------------------------
try:
    cur.execute("create extension if not exists vector;")
    print("✓ pgvector ready.")

    # Load embeddings to get dimension
    emb = np.load(EMB_PATH)
    if emb.ndim != 2:
        raise ValueError(f"Unexpected embeddings shape: {emb.shape}")
    n_rows, dim = emb.shape
    print(f"✓ Embeddings loaded: shape={emb.shape}")

    # Create table if not exists
    cur.execute(f"""
        create table if not exists {TABLE_NAME} (
          id text primary key,
          content text not null,
          source text default 'manual',
          model  text default 'text-embedding-3-small',
          embedding vector({dim}) not null,
          created_at timestamptz default now()
        );
    """)
    print(f"✓ Table '{TABLE_NAME}' ready.")

    # Create index if not exists
    cur.execute(f"""
        create index if not exists {TABLE_NAME}_embedding_cosine_idx
          on {TABLE_NAME} using ivfflat (embedding vector_cosine_ops)
          with (lists = 100);
    """)
    print("✓ Index ready.")
except Exception as e:
    cur.close()
    conn.close()
    sys.exit(f"Failed to prepare database objects: {e}")

# ------------------------
# Load metadata & sanity checks
# ------------------------
ids, texts, sources = [], [], []
try:
    with open(META_PATH, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            _id = parts[0]
            text = parts[1] if len(parts) > 1 else ""
            source = parts[2] if len(parts) > 2 else "unknown"
            ids.append(_id)
            texts.append(text)
            sources.append(source)
except Exception as e:
    cur.close()
    conn.close()
    sys.exit(f"Failed to read meta file: {e}")

if len(ids) != n_rows:
    cur.close()
    conn.close()
    sys.exit(f"Row mismatch: {len(ids)} meta lines vs {n_rows} embedding rows")

print(f"✓ Loaded {len(ids)} metadata entries")

# ------------------------
# Delete only existing CULPA documents
# ------------------------
print(f"\nDeleting existing CULPA documents (keeping bulletin data)...")
try:
    cur.execute(f"delete from {TABLE_NAME} where source like 'culpa.info%';")
    deleted_count = cur.rowcount
    print(f"✓ Deleted {deleted_count} old CULPA documents.")
except Exception as e:
    cur.close()
    conn.close()
    sys.exit(f"Failed to delete old CULPA documents: {e}")

# ------------------------
# Bulk insert in batches
# ------------------------
BATCH = 500
print(f"\nInserting {n_rows} CULPA chunks in batches of {BATCH}...")

try:
    conn.autocommit = False
    inserted_count = 0
    
    for start in tqdm(range(0, n_rows, BATCH), desc="Uploading"):
        end = min(start + BATCH, n_rows)
        batch_rows = []
        seen_ids = set()

        for i in range(start, end):
            # Skip duplicates
            if ids[i] in seen_ids:
                continue
            
            seen_ids.add(ids[i])
            vec_literal = to_vector_literal(emb[i])
            batch_rows.append((
                ids[i],
                texts[i],
                sources[i] if i < len(sources) else "unknown",
                "text-embedding-3-small",
                vec_literal,
            ))

        if not batch_rows:
            continue

        # Insert with conflict resolution
        insert_sql = f"""
            insert into {TABLE_NAME} (id, content, source, model, embedding)
            values %s
            on conflict (id) do update set
              content = excluded.content,
              source  = excluded.source,
              model   = excluded.model,
              embedding = excluded.embedding,
              created_at = now();
        """
        template = "(%s, %s, %s, %s, %s::vector)"
        execute_values(cur, insert_sql, batch_rows, template=template)
        inserted_count += len(batch_rows)

    # Refresh planner stats
    cur.execute(f"analyze {TABLE_NAME};")
    conn.commit()
    print(f"\n✓ Inserted {inserted_count} CULPA chunks successfully!")
except Exception as e:
    conn.rollback()
    cur.close()
    conn.close()
    sys.exit(f"Insert failed: {e}")

# ------------------------
# Final statistics
# ------------------------
try:
    cur.execute(f"select count(*) from {TABLE_NAME};")
    final_count = cur.fetchone()[0]
    
    cur.execute(f"select count(*) from {TABLE_NAME} where source like 'culpa.info%';")
    final_culpa_count = cur.fetchone()[0]
    
    cur.execute(f"select count(*) from {TABLE_NAME} where source not like 'culpa.info%';")
    bulletin_count = cur.fetchone()[0]
    
    print("\n" + "=" * 60)
    print("✅ Upload Complete!")
    print("=" * 60)
    print(f"Total documents in database: {final_count}")
    print(f"  - CULPA reviews: {final_culpa_count}")
    print(f"  - Bulletin data: {bulletin_count}")
    print("=" * 60)
except Exception as e:
    print(f"Warning: Could not fetch final statistics: {e}")

cur.close()
conn.close()
print("\n✓ Connection closed.")

