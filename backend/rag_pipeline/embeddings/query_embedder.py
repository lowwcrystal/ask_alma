from .json_embedder import compute_embeddings, convert_embeddings_to_vectors
from dotenv import load_dotenv
import os
from supabase import create_client
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
## compute query embeddings for the user query 
def query_embedder(query):
    return compute_embeddings("query", query)


if __name__ == "__main__":
    sample_query = ["What are the core classes for first year Columbia College students?"]
    query_embedding = query_embedder(sample_query)
    query_vector = convert_embeddings_to_vectors(query_embedding[0])
    response = supabase.rpc("hybrid_search_sql_debug", {
        "query_text": sample_query[0],
        "query_embedding": query_vector,
        "match_count": 5,
    }).execute()
       
