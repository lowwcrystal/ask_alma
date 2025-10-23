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
EMB_PATH = "emb_out/ollama_nomic-embed-text.npy"
META_PATH = "emb_out/ollama_nomic-embed-text.meta.tsv"
TABLE_NAME = "documents"  # change if you want a different table

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
    conn.autocommit = True  # for DDL convenience
    cur = conn.cursor()
    print("Connected to Supabase Postgres.")
except Exception as e:
    sys.exit(f"Failed to connect: {e}")

# ------------------------
# Ensure extension/table/index
# ------------------------
try:
    cur.execute("create extension if not exists vector;")
    print("pgvector ready.")

    # Load embeddings to get dimension
    emb = np.load(EMB_PATH)  # shape: (N, D)
    if emb.ndim != 2:
        raise ValueError(f"Unexpected embeddings shape: {emb.shape}")
    n_rows, dim = emb.shape
    print(f"Embeddings loaded: shape={emb.shape}")

    # Create table (id/content/source/model/embedding)
    cur.execute(f"""
        create table if not exists {TABLE_NAME} (
          id text primary key,
          content text not null,
          source text default 'manual',
          model  text default 'nomic-embed-text',
          embedding vector({dim}) not null,
          created_at timestamptz default now()
        );
    """)
    print(f"Table '{TABLE_NAME}' ready.")

    # ANN index for cosine distance (IVFFlat). Tune lists as needed.
    cur.execute(f"""
        create index if not exists {TABLE_NAME}_embedding_cosine_idx
          on {TABLE_NAME} using ivfflat (embedding vector_cosine_ops)
          with (lists = 100);
    """)
    print("Index ready.")
except Exception as e:
    cur.close()
    conn.close()
    sys.exit(f"Failed to prepare database objects: {e}")

# ------------------------
# Load metadata & sanity checks
# ------------------------
ids, texts = [], []
try:
    with open(META_PATH, "r", encoding="utf-8") as f:
        for line in f:
            _id, text = line.rstrip("\n").split("\t", 1)
            ids.append(_id)
            texts.append(text)
except Exception as e:
    cur.close()
    conn.close()
    sys.exit(f"Failed to read meta file: {e}")

if len(ids) != n_rows:
    cur.close()
    conn.close()
    sys.exit(f"Row mismatch: {len(ids)} meta lines vs {n_rows} embedding rows")

# ------------------------
# Bulk upsert in batches
# ------------------------
BATCH = 500
print(f"Upserting {n_rows} rows in batches of {BATCH}...")

try:
    # Switch to transactional mode for batch speed
    conn.autocommit = False
    for start in tqdm(range(0, n_rows, BATCH)):
        end = min(start + BATCH, n_rows)
        batch_rows = []

        for i in range(start, end):
            vec_literal = to_vector_literal(emb[i])
            batch_rows.append((
                ids[i],
                texts[i],
                "manual",             # source
                "nomic-embed-text",   # model (keep consistent)
                vec_literal,          # vector literal for pgvector
            ))

        # Fast bulk upsert with execute_values
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
        # Note: we cast the 5th column to vector in the template
        template = "(%s, %s, %s, %s, %s::vector)"
        execute_values(cur, insert_sql, batch_rows, template=template)

    # Refresh planner stats for better ANN behavior
    cur.execute(f"analyze {TABLE_NAME};")
    conn.commit()
    print("Upsert complete.")
except Exception as e:
    conn.rollback()
    cur.close()
    conn.close()
    sys.exit(f"Upsert failed: {e}")

cur.close()
conn.close()
print("Connection closed.")