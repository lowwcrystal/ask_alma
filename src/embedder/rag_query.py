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
# Load from .env in the same directory as this file
local_env = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(local_env):
    load_dotenv(local_env)
else:
    load_dotenv()  # Fall back to default location 

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

SCHOOL_LABELS = {
    "columbia_college": "Columbia College",
    "columbia_engineering": "Columbia Engineering",
    "barnard": "Barnard College",
}

SCHOOL_SOURCE_PATTERNS = {
    "columbia_college": "%columbia_college%",
    "columbia_engineering": "%columbia_engineering%",
    "barnard": "%barnard%",
}

# -------------------------------
# Helpers
# -------------------------------
def get_pg_conn():
   
    
    url = os.getenv("DATABASE_URL")
    if url:
        if "sslmode=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}sslmode=require"
        return psycopg2.connect(url, cursor_factory=RealDictCursor)
    raise SystemExit("Missing DB settings. Set DATABASE_URL in .env")

# -------------------------------
# Conversation Management
# -------------------------------
def create_conversation(conn, user_id=None) -> str:
    """Create a new conversation and return its ID."""
    cur = conn.cursor()
    if user_id:
        cur.execute("INSERT INTO conversations (user_id) VALUES (%s) RETURNING id;", (user_id,))
    else:
        cur.execute("INSERT INTO conversations DEFAULT VALUES RETURNING id;")
    conversation_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    return str(conversation_id)


def get_school_source_filter(school: Optional[str]) -> Optional[str]:
    """Return a source filter pattern for the student's school, if available."""
    if not school:
        return None
    return SCHOOL_SOURCE_PATTERNS.get(school)


def get_user_profile(conn, user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Fetch profile information for a Supabase user, if available."""
    if not user_id:
        return None
    cur = conn.cursor()
    cur.execute("""
        SELECT school, academic_year, major, minors, classes_taken, profile_image
        FROM user_profiles
        WHERE user_id = %s;
    """, (user_id,))
    profile = cur.fetchone()
    cur.close()
    return profile


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


def format_profile_summary(profile: Dict[str, Any]) -> Optional[str]:
    """Format profile details into natural language instructions."""
    if not profile:
        return None

    lines = []
    school_value = profile.get("school")
    school_label = SCHOOL_LABELS.get(school_value, school_value) if school_value else None
    if school_label:
        lines.append(f"- School: {school_label}")
    if profile.get("academic_year"):
        lines.append(f"- Academic year: {profile['academic_year']}")
    if profile.get("major"):
        lines.append(f"- Major: {profile['major']}")
    minors = profile.get("minors") or []
    if minors:
        lines.append(f"- Minors: {', '.join(minors)}")
    classes_taken = profile.get("classes_taken") or []
    if classes_taken:
        lines.append(f"- Classes already completed: {', '.join(classes_taken)}")

    if not lines:
        return None

    if school_label:
        lines.append(f"- Prioritize information from {school_label} sources when relevant.")
    lines.append("- Do not recommend courses that are already completed.")
    return "\n".join(lines)


def build_prompt(
    question: str,
    contexts: list[str],
    chat_history: List[Dict[str, Any]] = None,
    profile_summary: Optional[str] = None,
) -> str:
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

    profile_text = ""
    if profile_summary:
        profile_text = f"\n\nSTUDENT PROFILE:\n{profile_summary}\n"
    
    return textwrap.dedent(f"""
    You are AskAlma, an expert academic advisor for students at Columbia College, Columbia Engineering, Columbia GS, and Barnard College.
    
    ## YOUR ROLE & BEHAVIOR:
    You are a VERSATILE academic advisor who can help with a wide range of academic questions, including:
    - Course information (descriptions, prerequisites, credits, workload, when offered)
    - Professor and department research areas
    - Major and minor requirements
    - Degree program structures and tracks
    - Semester and academic planning
    - Registration policies and procedures
    - Academic deadlines and timelines
    
    Be conversational, friendly, and supportive while maintaining accuracy. Always base your answers on the CONTEXT provided below.{profile_text}
    
    ## WHEN TO USE CHAT HISTORY:
    **IMPORTANT**: Only reference chat history when the current question is DIRECTLY RELATED to previous conversation.
    
    **Use chat history when:**
    - Question uses referential words: "it", "that course", "those classes", "what about the other one"
    - Question is a clear follow-up: "What are the prerequisites?" (after discussing a specific course)
    - Question asks about previously mentioned information: "What else did I take?"
    - Building on a previous topic: continuing a semester planning discussion
    
    **DO NOT use chat history when:**
    - Question is completely unrelated to previous conversation (new topic, different course, different question type)
    - Question is self-contained and doesn't reference prior context
    - Student asks about something entirely different
    
    **Example:**
    - Previous: "Tell me about COMS 3134"
    - Current: "What are the prerequisites?" → USE history (prerequisites for COMS 3134)
    - Current: "What is PSYC 1001 about?" → IGNORE history (new unrelated question)
    
    ## TYPES OF QUESTIONS YOU CAN ANSWER:
    
    ### 1. Course Information Queries
    Answer directly and concisely:
    - "What is [COURSE CODE/COURSE NAME] about?" → Provide course description
    - "How many credits is [COURSE]?" → State the credits
    - "What are prerequisites for [COURSE]?" → List prerequisites
    - "When is [COURSE] offered?" → State Fall/Spring/Both
    - "Who teaches [COURSE]?" → Name instructors if available
    - "Is [COURSE] hard?" → Mention workload if in context
    
    ### 2. Academic Program Queries
    - "What are the requirements for [MAJOR]?" → List major requirements
    - "What tracks exist in [MAJOR]?" → Explain available tracks
    - "What's the difference between [PROGRAM A] and [PROGRAM B]?" → Compare
    
    ### 3. Professor/Research Queries
    - "What does Professor [NAME] research?" → Describe research areas
    - "Who teaches in the [DEPARTMENT]?" → List faculty
    
    ### 4. Planning and Recommendations (detailed rules below)
    
    ## RULES FOR COURSE RECOMMENDATIONS AND PLANNING:
    **These rules apply ONLY when making course recommendations or creating semester plans:**
    
    - Always tailor suggestions to the student's academic year, major, and minors (from the student profile).
    - Never recommend courses that the student has already completed. Acknowledge completed courses explicitly.

    1. **NEVER suggest courses the student has already taken**
       - Review conversation history for courses mentioned as "taken", "completed", or "finished"
       - Explicitly acknowledge completed courses and exclude them from recommendations
       - Double-check before recommending ANY course
    
    2. **Follow major-specific requirements and tracks**
       - Check prerequisites, corequisites, and course sequences from the CONTEXT
       - Respect major tracks (e.g., CS tracks, Engineering concentrations)
       - Consider course load balance (don't overload with difficult courses)
       - Follow specific degree requirements for their school and major
    
    3. **Verify prerequisites carefully**
       - Only suggest courses where prerequisites are met based on courses taken
       - If prerequisites are unclear, mention them explicitly
       - Don't assume prerequisites are met without evidence
    
    4. **Consider timing and availability**
       - Note which semester courses are typically offered (Fall/Spring)
       - Respect course sequencing (e.g., Core Curriculum timing)
       - Mention if a course is typically for specific year levels
       - If a course is only offered in Fall or Spring, mention it explicitly
    
    ## WHEN TO ASK FOR MORE INFORMATION:
    **Only when creating personalized plans or recommendations**, if the student hasn't provided:
    - Their year (Freshman, Sophomore, Junior, Senior)
    - Their major and concentration/track
    - List of courses already completed
    - Academic goals or schedule preferences
    
    Ask for this information before making specific recommendations.
    
    **For simple factual questions (course info, requirements, etc.)**: Answer directly without asking for context.
    
    ## RESPONSE FORMATS:
    
    ### For Factual Questions (Course Info, Requirements, etc.)
    Be direct and concise:
    - Answer the specific question asked
    - Include relevant details from context
    - No need for elaborate formatting unless listing multiple items
    
    ### For Semester Planning:
    Structure your response:
    
    1. **Acknowledge their background**: "Based on your completed courses: [list], and your [major/track]..."
    2. **Provide course recommendations** in this format:
       - **[COURSE CODE] - [Title]** (X credits)
       - Fulfills: [requirement type]
       - Why recommended: [specific reason]
       - Prerequisites: [status]
    3. **Summary**: Total credits, progression toward goals
    4. **Alternatives**: Mention 1-2 alternative options if applicable
    
    ## ACCURACY & VERIFICATION:
    - Base ALL answers on the CONTEXT provided below
    - If information is missing: "I don't see information about [X] in the course bulletins"
    - Never invent course codes, requirements, or prerequisites
    - Cite sources when making definitive statements (e.g., "According to the CS major requirements...")
    - If context is insufficient, tell the student what information is missing
    
    ## FOR NON-ACADEMIC QUESTIONS:
    If asked something unrelated to academics/college life, give a brief, friendly response, then gently redirect to academic topics.
    {history_text}
    ═══════════════════════════════════════════════════════════
    CONTEXT FROM COURSE BULLETINS AND ACADEMIC REQUIREMENTS:
    ═══════════════════════════════════════════════════════════
    {context_text}
    
    ═══════════════════════════════════════════════════════════
    STUDENT'S QUESTION:
    ═══════════════════════════════════════════════════════════
    {question}
    
    ═══════════════════════════════════════════════════════════
    CRITICAL REMINDERS BEFORE ANSWERING:
    ═══════════════════════════════════════════════════════════
    ✓ What type of question is this? (factual info vs. planning/recommendations)
    ✓ Is this related to the previous conversation? (should I use chat history?)
    ✓ Do I have the information needed in the CONTEXT to answer accurately?
    ✓ If making recommendations: Have they mentioned courses already taken?
    ✓ If making recommendations: Do I need to ask for more information first?
    
    **Response approach based on question type:**
    - Factual question about courses/requirements → Answer directly from context
    - Personalized planning → Check for completed courses, ask for missing info if needed
    - Follow-up question → Reference chat history if relevant
    - Unrelated new question → Ignore chat history, focus on current question
    """)

# -------------------------------
# Main query function
# -------------------------------
def rag_answer(
    question: str, 
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
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
    profile = get_user_profile(conn, user_id)
    profile_summary = format_profile_summary(profile) if profile else None
    
    # 1) Handle conversation
    chat_history = []
    if conversation_id:
        # Load existing conversation history
        chat_history = get_conversation_history(conn, conversation_id)
    elif save_to_db:
        # Create a new conversation
        conversation_id = create_conversation(conn, user_id=user_id)
    
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
    # Prioritize 2026 sources, fall back to 2024-2025 if needed
    vec_literal = "[" + ",".join(f"{x:.8f}" for x in q_vec) + "]"

    rows = []
    school_filter = get_school_source_filter(profile.get("school") if profile else None)
    
    # Define 2026 source patterns (prioritized)
    sources_2026 = ["seas_2026.json", "barnard_2026.json", "columbia_college_2026.json"]
    
    # Step 1: Get results from 2026 sources first (prioritized)
    # Build 2026 source filter
    source_2026_filter = " OR ".join([f"source ILIKE '%{s}%'" for s in sources_2026])
    
    if school_filter:
        # If user has school filter, apply it to 2026 sources
        priority_sql = f"""
            select
              id,
              content,
              1 - (embedding <=> %s::vector) as similarity,
              source
            from {table_name}
            where ({source_2026_filter}) AND source ILIKE %s
            order by embedding <=> %s::vector
            limit %s;
        """
        cur.execute(priority_sql, (vec_literal, school_filter, vec_literal, TOP_K))
    else:
        # No school filter, get all 2026 sources
        priority_sql = f"""
            select
              id,
              content,
              1 - (embedding <=> %s::vector) as similarity,
              source
            from {table_name}
            where {source_2026_filter}
            order by embedding <=> %s::vector
            limit %s;
        """
        cur.execute(priority_sql, (vec_literal, vec_literal, TOP_K))
    
    priority_rows = cur.fetchall()
    rows.extend(priority_rows)
    existing_ids = {row["id"] for row in rows}
    
    # Step 2: Fill remaining slots with 2024-2025 sources if needed
    if len(rows) < TOP_K:
        remaining = TOP_K - len(rows)
        
        # Build exclusion for 2026 sources
        exclude_2026 = " AND ".join([f"source NOT ILIKE '%{s}%'" for s in sources_2026])
        
        if school_filter:
            fallback_sql = f"""
                select
                  id,
                  content,
                  1 - (embedding <=> %s::vector) as similarity,
                  source
                from {table_name}
                where source ILIKE %s AND {exclude_2026}
                order by embedding <=> %s::vector
                limit %s;
            """
            cur.execute(fallback_sql, (vec_literal, school_filter, vec_literal, remaining))
        else:
            fallback_sql = f"""
                select
                  id,
                  content,
                  1 - (embedding <=> %s::vector) as similarity,
                  source
                from {table_name}
                where {exclude_2026}
                order by embedding <=> %s::vector
                limit %s;
            """
            cur.execute(fallback_sql, (vec_literal, vec_literal, remaining))
        
        fallback_rows = cur.fetchall()
        # Filter out duplicates and add to results
        for row in fallback_rows:
            if row["id"] not in existing_ids:
                rows.append(row)
                existing_ids.add(row["id"])
                if len(rows) >= TOP_K:
                    break
    
    # Sort final results by similarity (2026 results should naturally rank higher due to better matches)
    rows = sorted(rows, key=lambda x: x["similarity"], reverse=True)[:TOP_K]

    cur.close()

    contexts = [row["content"] for row in rows]
    
    # 4) Build prompt with chat history
    prompt = build_prompt(question, contexts, chat_history, profile_summary)

    

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
        if profile_summary:
            metadata["student_profile_summary"] = profile_summary
        if school_filter and filtered_rows:
            metadata["school_filter_applied"] = school_filter
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