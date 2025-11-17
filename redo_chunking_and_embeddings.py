#!/usr/bin/env python3
"""
Script to redo all chunking, delete existing embeddings, and re-embed everything.
"""

import os
import sys
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

print("=" * 60)
print("🔄 REDOING ALL CHUNKING AND EMBEDDINGS")
print("=" * 60)

# Step 1: Delete all existing embeddings
print("\n1️⃣  Deleting all existing embeddings from database...")
try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()
    
    # Count existing rows
    cur.execute("SELECT COUNT(*) FROM documents;")
    count = cur.fetchone()[0]
    print(f"   Found {count} existing embeddings")
    
    # Delete all rows
    cur.execute("DELETE FROM documents;")
    deleted = cur.rowcount
    conn.commit()
    print(f"   ✓ Deleted {deleted} embeddings")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"   ✗ Error deleting embeddings: {e}")
    sys.exit(1)

# Step 2: Run chunking
print("\n2️⃣  Running chunking process...")
print("   (This will create chunks with minimum 2000 characters)")
os.system("cd /Users/crystallow/ask_alma && venv/bin/python3 src/chunking/data_chunking.py")

# Step 3: Run embedding
print("\n3️⃣  Generating embeddings...")
print("   (This may take a while)")
os.system("cd /Users/crystallow/ask_alma/src/embedder && ../../venv/bin/python3 embedder.py")

# Step 4: Upload embeddings
print("\n4️⃣  Uploading embeddings to Supabase...")
os.system("cd /Users/crystallow/ask_alma/src/embedder && ../../venv/bin/python3 upload_embeddings.py")

print("\n" + "=" * 60)
print("✅ ALL DONE!")
print("=" * 60)

