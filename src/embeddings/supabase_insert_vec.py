import os
from supabase import create_client
from tqdm import tqdm
import json
import json_embedder
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
BATCH_SIZE = 128

def insert_embeddings(texts, batch_size):
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding + Inserting"):
        batch_texts = texts[i:i + batch_size]

        batch_embeddings = json_embedder.compute_embeddings(batch_texts)
        batch_vectors = json_embedder.convert_embeddings_to_vectors(batch_embeddings)
        
        rows = []
        for text, vector in zip(batch_texts, batch_vectors):
            rows.append({
                "content": text,
                "embedding": vector
        })
        try: 
            supabase.table("documents").insert(rows).execute()
        except Exception as e:
            print(f"Error inserting batch starting at index {i}: {e}")
if __name__ == "__main__":

    path = "chunked_bulletins.jsonl"
    texts = []
    with open(path, "r", encoding="utf-8") as file:
        for record in file:
            file_line = json.loads(record)
            texts.append(file_line["text"])
    insert_embeddings(texts, batch_size=BATCH_SIZE)
