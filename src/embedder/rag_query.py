# rag_query.py
import os
import textwrap
import json
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import uuid

# Load environment variables (OPENAI_API_KEY, DATABASE_URL)
load_dotenv()

# Embeddings + LLM
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_ollama import ChatOllama

# -------------------------------
# Config
# -------------------------------
EMBED_MODEL = "text-embedding-3-small"  # must match what you used to index

# LLM Provider: "openai" or "ollama"
LLM_PROVIDER = "openai"  # Change to "ollama" to use local Ollama models

# Model configurations
OPENAI_MODELS = {
    "gpt-4o": "gpt-4o",              # Most capable, good for complex reasoning
    "gpt-4o-mini": "gpt-4o-mini",    # Fast and affordable, great balance
    "gpt-4-turbo": "gpt-4-turbo-preview",  # Previous generation, still powerful
    "gpt-3.5-turbo": "gpt-3.5-turbo" # Cheapest, fastest, good for simple queries
}

OLLAMA_MODELS = {
    "llama3.1": "llama3.1",
    "llama3.2": "llama3.2",
    "mistral": "mistral",
    "gemma2": "gemma2"
}

# Choose your model
OPENAI_MODEL = "gpt-4o-mini"  # Which OpenAI model to use
OLLAMA_MODEL = "llama3.1"     # Which Ollama model to use

TOP_K       = 10                   # how many chunks to retrieve
MAX_CONTEXT_CHARS = 8000           # safety to avoid overlong prompts
MAX_HISTORY_MESSAGES = 10          # how many previous messages to include in context
LLM_TEMPERATURE = 0.2              # 0 = deterministic, 1 = creative

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
    return psycopg2.connect(
        host=host, port=port, dbname=db, user=user, password=pwd, sslmode="require",
        cursor_factory=RealDictCursor
    )

# -------------------------------
# Conversation Management
# -------------------------------
def create_conversation(conn) -> str:
    """Create a new conversation and return its ID."""
    cur = conn.cursor()
    cur.execute("INSERT INTO conversations DEFAULT VALUES RETURNING id;")
    conversation_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    return str(conversation_id)


def get_conversation_history(conn, conversation_id: str, limit: int = MAX_HISTORY_MESSAGES) -> List[Dict[str, Any]]:
    """Retrieve the last N messages from a conversation."""
    cur = conn.cursor()
    cur.execute("""
        SELECT role, content, created_at, metadata
        FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at DESC
        LIMIT %s;
    """, (conversation_id, limit))
    messages = cur.fetchall()
    cur.close()
    # Reverse to get chronological order
    return list(reversed(messages))


def save_message(conn, conversation_id: str, role: str, content: str, metadata: Dict[str, Any] = None):
    """Save a message to the conversation history."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages (conversation_id, role, content, metadata)
        VALUES (%s, %s, %s, %s);
    """, (conversation_id, role, content, json.dumps(metadata or {})))
    conn.commit()
    cur.close()


def build_prompt(question: str, contexts: list[str], chat_history: List[Dict[str, Any]] = None) -> str:
    """Constructs a RAG prompt with optional chat history for llama3.1."""
    context_text = "\n\n---\n\n".join(contexts)
    # Truncate context if it's too long
    context_text = context_text[:MAX_CONTEXT_CHARS]
    
    # Build chat history section
    history_text = ""
    if chat_history:
        history_lines = []
        for msg in chat_history:
            role = msg["role"].upper()
            content = msg["content"]
            history_lines.append(f"{role}: {content}")
        history_text = "\n\nCHAT HISTORY:\n" + "\n\n".join(history_lines) + "\n"
    
    return textwrap.dedent(f"""
    You are AskAlma, a helpful academic assistant for students in Columbia College, Columbia Engineering, Columbia GS and Barnard College. 

    Use the CONTEXT to answer the QUESTION. If the context is insufficient, say you're not certain.
    No need to repeat the question in the answer, just answer the question in a concise, well-structured paragraph, list, or short answer. Only answer with paragraphs if the question is specific. For more general questions, respon with a short and concise answer.
    {history_text}
    CONTEXT:
    {context_text}
    QUESTION:
    {question}

    Answer in a concise, well-structured paragraph. If there are prerequisites, schedules, or course codes, be precise.
    If the question refers to previous context (using words like "that", "it", "those"), use the chat history to understand what they're referring to.
    """)

# -------------------------------
# Main query function
# -------------------------------
def rag_answer(
    question: str, 
    conversation_id: Optional[str] = None,
    table_name: str = "documents", 
    probes: int = 10,
    save_to_db: bool = True
) -> dict:
    """
    1) Load conversation history (if conversation_id provided)
    2) Embed the question with OpenAI embeddings
    3) Retrieve TOP_K most similar chunks from pgvector (cosine distance)
    4) Generate an answer with llama3.1 using retrieved context + chat history
    5) Save the question and answer to the database (if save_to_db=True)
    
    Args:
        question: User's question
        conversation_id: UUID of existing conversation, or None to create new one
        table_name: Name of the documents table
        probes: IVFFlat probes parameter for search accuracy
        save_to_db: Whether to save messages to database
    
    Returns:
        Dictionary with answer, matches, conversation_id, and other metadata
    """
    # Connect to database
    conn = get_pg_conn()
    
    # 1) Handle conversation
    chat_history = []
    if conversation_id:
        # Load existing conversation history
        chat_history = get_conversation_history(conn, conversation_id)
    elif save_to_db:
        # Create a new conversation
        conversation_id = create_conversation(conn)
    
    # 2) Get query embedding
    embedder = OpenAIEmbeddings(model=EMBED_MODEL)
    q_vec = embedder.embed_query(question)  # -> list[float]

    # 3) Retrieve from Postgres
    cur = conn.cursor()

    # Improve ANN recall (IVFFlat): set probes (tune 5-20)
    try:
        cur.execute("set ivfflat.probes = %s;", (probes,))
    except Exception:
        pass  # if extension/version doesn't support it, ignore

    # Query top-k (cosine distance). Similarity = 1 - distance.
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
    cur.close()

    contexts = [row["content"] for row in rows]
    
    # 4) Build prompt with chat history
    prompt = build_prompt(question, contexts, chat_history)

    

    # 5) Generate answer with chosen LLM
    if LLM_PROVIDER == "openai":
        llm = ChatOpenAI(
            model=OPENAI_MODELS[OPENAI_MODEL],
            temperature=LLM_TEMPERATURE
        )
        gen_model_name = f"openai:{OPENAI_MODEL}"
    else:  # ollama
        llm = ChatOllama(
            model=OLLAMA_MODELS[OLLAMA_MODEL],
            base_url="http://localhost:11434",
            temperature=LLM_TEMPERATURE
        )
        gen_model_name = f"ollama:{OLLAMA_MODEL}"
    
    answer = llm.invoke(prompt).content

    # 6) Save to database
    if save_to_db and conversation_id:
        # Save user message
        save_message(conn, conversation_id, "user", question)
        
        # Save assistant response with metadata about retrieved chunks
        metadata = {
            "top_matches": [
                {
                    "id": row["id"],
                    "similarity": float(row["similarity"]),
                    "content_preview": row["content"][:200]
                }
                for row in rows[:5]  # Save top 5 matches
            ]
        }
        save_message(conn, conversation_id, "assistant", answer, metadata)
    
    conn.close()

    return {
        "conversation_id": conversation_id,
        "question": question,
        "answer": answer,
        "matches": rows,   # includes id, content, similarity
        "chat_history": chat_history,
        "used_model_embed": EMBED_MODEL,
        "used_model_llm": gen_model_name,
    }

# -------------------------------
# CLI usage
# -------------------------------
if __name__ == "__main__":
    print("\n" + "="*80)
    print("AskAlma - Academic Assistant with Conversation Context")
    print("="*80)
    
    # Example: Start a new conversation
    print("\n--- Starting NEW conversation ---\n")
    q1 = "What are the core classes for first year Columbia College students?"
    result1 = rag_answer(q1, conversation_id=None, save_to_db=True)
    
    print(f"Q: {q1}")
    print(f"\nA: {result1['answer']}")
    print(f"\n[Conversation ID: {result1['conversation_id']}]")
    
    # Example: Continue the conversation with a follow-up question
    print("\n" + "─"*80)
    print("\n--- Follow-up question in SAME conversation ---\n")
    conversation_id = result1['conversation_id']
    q2 = "What are the prerequisites for those classes?"
    result2 = rag_answer(q2, conversation_id=conversation_id, save_to_db=True)
    
    print(f"Q: {q2}")
    print(f"\nA: {result2['answer']}")
    
    # Example: Another follow-up
    print("\n" + "─"*80)
    print("\n--- Another follow-up question ---\n")
    q3 = "How many credits are they worth in total?"
    result3 = rag_answer(q3, conversation_id=conversation_id, save_to_db=True)
    
    print(f"Q: {q3}")
    print(f"\nA: {result3['answer']}")
    
    # Show conversation history
    print("\n" + "="*80)
    print("=== CONVERSATION HISTORY ===")
    print("="*80)
    for msg in result3['chat_history']:
        role_icon = "🧑" if msg['role'] == 'user' else "🤖"
        print(f"\n{role_icon} {msg['role'].upper()}:")
        print(msg['content'])
    
    # Show retrieved chunks for the last query
    print("\n" + "="*80)
    print(f"=== TOP {TOP_K} MOST SIMILAR CHUNKS (for last query) ===")
    print("="*80)
    
    for i, r in enumerate(result3["matches"], 1):
        print(f"\n{'─'*80}")
        print(f"[{i}] SIMILARITY: {r['similarity']:.4f} | ID: {r['id']}")
        print(f"{'─'*80}")
        print(r['content'])
        print(f"{'─'*80}")