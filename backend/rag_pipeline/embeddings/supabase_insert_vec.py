import os
from supabase import create_client
from tqdm import tqdm
import json
from . import json_embedder
from dotenv import load_dotenv
import hashlib
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
BATCH_SIZE = 128

def insert_embeddings(records, batch_size):
    for i in tqdm(range(0, len(records), batch_size), desc="Embedding + Inserting"):
        curr_batch = records[i:i + batch_size]
        batch_texts   = [record["text"]  for record in curr_batch]
        batch_sources = [record["source"] for record in curr_batch]

        batch_embeddings = json_embedder.compute_embeddings("passage", batch_texts)
        batch_vectors = json_embedder.convert_embeddings_to_vectors(batch_embeddings)
        
        rows = []
        for text, vector, source in zip(batch_texts, batch_vectors, batch_sources):
            file_name = source.split("/")[-1].replace(".pdf", "").split(" ")
            school = file_name[0]
            year = file_name[1]
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

            rows.append({
                "content": text,
                "embedding": vector,
                "source": source,
                "school": school,
                "year": year,
                "content_hash": content_hash
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
            texts.append(file_line)
    insert_embeddings(texts, batch_size=BATCH_SIZE)
