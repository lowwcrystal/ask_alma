# rag_query.py
import os
import textwrap
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Embeddings + LLM via Ollama
from langchain_ollama import OllamaEmbeddings, ChatOllama

# -------------------------------
# Config
# -------------------------------
EMBED_MODEL = "nomic-embed-text"  # must match what you used to index
GEN_MODEL   = "llama3.1"
TOP_K       = 5                    # how many chunks to retrieve
MAX_CONTEXT_CHARS = 8000           # safety to avoid overlong prompts

# -------------------------------
# Helpers
# -------------------------------
def get_pg_conn():
    """Connect to Supabase Postgres using either DATABASE_URL"""
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if url:
        if "sslmode=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}sslmode=require"
        return psycopg2.connect(url, cursor_factory=RealDictCursor)
    raise SystemExit("Missing DB settings. Set DATABASE_URL in .env")

def build_prompt(question: str, contexts: list[str]) -> str:
    """Constructs a simple RAG prompt for llama3.1."""
    context_text = "\n\n---\n\n".join(contexts)
    # Truncate context if it's too long
    context_text = context_text[:MAX_CONTEXT_CHARS]
    return textwrap.dedent(f"""
    You are AskAlma, a helpful academic assistant for students in Columbia College, Columbia Engineering, Columbia GS and Barnard College. 

    Use the CONTEXT to answer the QUESTION. If the context is insufficient, say you’re not certain.

    CONTEXT:
    {context_text}

    QUESTION:
    {question}

    Answer in a concise, well-structured paragraph. If there are prerequisites, schedules, or course codes, be precise.
    """)

# -------------------------------
# Main query function
# -------------------------------
def rag_answer(question: str, table_name: str = "documents", probes: int = 10) -> dict:
    """
    1) Embed the question with Ollama embeddings
    2) Retrieve TOP_K most similar chunks from pgvector (cosine distance)
    3) Generate an answer with llama3.1 using the retrieved context
    """
    # 1) Get query embedding
    embedder = OllamaEmbeddings(model=EMBED_MODEL, base_url="http://localhost:11434")
    q_vec = embedder.embed_query(question)  # -> list[float]

    # 2) Retrieve from Postgres
    conn = get_pg_conn()
    cur = conn.cursor()

    # Improve ANN recall (IVFFlat): set probes (tune 5-20)
    try:
        cur.execute("set ivfflat.probes = %s;", (probes,))
    except Exception:
        pass  # if extension/version doesn't support it, ignore

    # Query top-k (cosine distance). Similarity = 1 - distance.
    # NOTE: %s binds are safe. pgvector expects an array; we cast to vector.
    sql = f"""
        select
          id,
          content,
          1 - (embedding <=> %s::vector) as similarity
        from {table_name}
        order by embedding <=> %s::vector
        limit %s;
    """
    # psycopg2 needs the vector as a string like '[0.1,0.2,...]'
    vec_literal = "[" + ",".join(f"{x:.8f}" for x in q_vec) + "]"
    cur.execute(sql, (vec_literal, vec_literal, TOP_K))
    rows = cur.fetchall()
    cur.close(); conn.close()

    contexts = [row["content"] for row in rows]
    prompt = build_prompt(question, contexts)

    # 3) Generate with llama3.1
    llm = ChatOllama(model=GEN_MODEL, base_url="http://localhost:11434", temperature=0.2)
    answer = llm.invoke(prompt).content

    return {
        "question": question,
        "answer": answer,
        "matches": rows,   # includes id, content, similarity
        "used_model_embed": EMBED_MODEL,
        "used_model_llm": GEN_MODEL,
    }

# -------------------------------
# CLI usage
# -------------------------------
if __name__ == "__main__":
    # Example question; replace with your own.
    q = "Which course requires calculus, and what are the prerequisites?"
    result = rag_answer(q, table_name="documents", probes=10)

    print("\n=== ANSWER ===\n")
    print(result["answer"])

    print("\n=== TOP MATCHES ===")
    for i, r in enumerate(result["matches"], 1):
        print(f"\n[{i}] similarity={r['similarity']:.3f}  id={r['id']}\n{r['content'][:300]}...")