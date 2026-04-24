# rag_query.py
import os
import textwrap
import json
import re
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

TOP_K       = 6                   # how many chunks to retrieve
MAX_CONTEXT_CHARS = 5000           # safety to avoid overlong prompts
MAX_HISTORY_MESSAGES = 6          # how many previous messages to include in context
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


def get_school_source_filter(school: Optional[str]) -> Optional[tuple]:
    """
    Return source filter patterns for the student's school, if available.
    Returns a tuple: (included_patterns, excluded_patterns)
    - For Columbia College or SEAS: includes both Columbia sources, excludes Barnard
    - For Barnard: includes only Barnard, excludes Columbia sources
    """
    if not school:
        return None
    
    # Group Columbia College and SEAS together
    if school in ["columbia_college", "columbia_engineering"]:
        # Include both Columbia sources, exclude Barnard
        return (
            [SCHOOL_SOURCE_PATTERNS["columbia_college"], SCHOOL_SOURCE_PATTERNS["columbia_engineering"]],
            [SCHOOL_SOURCE_PATTERNS["barnard"]]
        )
    elif school == "barnard":
        # Include only Barnard, exclude Columbia sources
        return (
            [SCHOOL_SOURCE_PATTERNS["barnard"]],
            [SCHOOL_SOURCE_PATTERNS["columbia_college"], SCHOOL_SOURCE_PATTERNS["columbia_engineering"]]
        )
    
    # Fallback to original behavior for unknown schools
    return ([SCHOOL_SOURCE_PATTERNS.get(school)], None)


def get_user_profile(conn, user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Fetch profile information for a Supabase user, if available."""
    if not user_id:
        return None
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT school, academic_year, major, minors, classes_taken, profile_image
            FROM user_profiles
            WHERE user_id = %s;
        """, (user_id,))
        profile = cur.fetchone()
        
        # If no profile found, return None
        if not profile:
            return None
            
        # Ensure we return a dict (RealDictCursor should handle this, but be safe)
        if not isinstance(profile, dict):
            # Convert tuple to dict if needed
            columns = ['school', 'academic_year', 'major', 'minors', 'classes_taken', 'profile_image']
            profile = dict(zip(columns, profile))
        return profile
    except Exception as e:
        print(f"Error fetching user profile for {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        cur.close()


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
    - Professor reviews and teaching styles (from CULPA student feedback)
    - Professor research areas and department information
    - Major and minor requirements
    - Degree program structures and tracks
    - Semester and academic planning
    - Registration policies and procedures
    - Academic deadlines and timelines
    
    Be conversational, friendly, and supportive while maintaining accuracy. Always base your answers on the CONTEXT provided below.
    
    **IMPORTANT FOR SCHOOL-SPECIFIC QUESTIONS**: When a student's profile indicates a specific school, prioritize information accordingly:
    - For Columbia College or SEAS students: Prioritize information from both Columbia College and SEAS sources (they share many requirements and resources)
    - For Barnard students: Prioritize information from Barnard-specific sources
    Look for school-specific requirements, terminology, and course listings in the context.{profile_text}
    
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
    - Current: "What are the prerequisites?" -> USE history (prerequisites for COMS 3134)
    - Current: "What is PSYC 1001 about?" -> IGNORE history (new unrelated question)
    
    ## TYPES OF QUESTIONS YOU CAN ANSWER:
    
    ### 1. Course Information Queries
    Answer directly and concisely:
    - "What is [COURSE CODE/COURSE NAME] about?" -> Provide course description
    - "How many credits is [COURSE]?" -> State the credits
    - "What are prerequisites for [COURSE]?" -> List prerequisites
    - "When is [COURSE] offered?" -> State Fall/Spring/Both
    - "Who teaches [COURSE]?" -> Name instructors if available
    - "Is [COURSE] hard?" -> Mention workload if in context
    
    ### 2. Academic Program Queries
    - "What are the requirements for [MAJOR]?" -> List major requirements
    - "What tracks exist in [MAJOR]?" -> Explain available tracks
    - "What's the difference between [PROGRAM A] and [PROGRAM B]?" -> Compare
    
    ### 3. Professor/Research Queries
    - "What does Professor [NAME] research?" -> Describe research areas
    - "Who teaches in the [DEPARTMENT]?" -> List faculty
    
    ### 4. Professor Review Queries (from CULPA student reviews)
    **When answering questions about professor reviews, teaching style, or student opinions:**
    
    **Provide balanced, fair, and comprehensive reviews:**
    - Include BOTH positive and negative feedback from students
    - Highlight frequently mentioned points (teaching style, workload, grading, accessibility)
    - Mention specific examples from student reviews when available
    - Cite the overall rating (e.g., "Professor X has an overall rating of 3.8/5.0")
    - Cover key aspects: teaching effectiveness, clarity, workload, grading fairness, approachability
    - End with a balanced summary that helps students make informed decisions
    
    **For professor comparisons:**
    - Give equal coverage to both/all professors being compared
    - Use fair, objective language based on student feedback
    - Compare on similar dimensions (teaching style, workload, grading, accessibility)
    - Acknowledge that experiences vary and one professor isn't necessarily "better" overall
    - Help students make informed decisions based on their preferences (e.g., "If you prefer clear lectures, Professor A might be better; if you want more discussion, consider Professor B")
    
    **Handle partial or informal names flexibly:**
    - Students may use only last names (e.g., "Professor Borowski" instead of "Brian Borowski")
    - Students may use only first names or nicknames in some cases
    - Be flexible with the name and use the context to help you find the correct professor
    - If you find reviews in context matching the partial name, use them
    - If NO matching professor is found in the context:
      * Say: "I don't have reviews for a professor by that name in my database."
      * If there are similar names in the context, suggest them: "Did you mean Professor [Full Name] or Professor [Other Similar Name]?"
      * Be helpful: "Could you provide the full name or the course they teach?"
    
    ### 5. Planning and Recommendations (detailed rules below)
    
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
      - Related requirements or categories that might contain the information
      - School-specific terminology (Barnard, Columbia College, SEAS may use different terms)
    - **SCHOOL-SPECIFIC PRIORITY**: If the student's profile indicates a specific school:
      - For Columbia College or SEAS students: Prioritize information from both Columbia College and SEAS sources (they share many requirements and resources)
      - For Barnard students: Prioritize information from Barnard-specific sources
      - Use school-specific terminology and requirements
      - If information exists in the context but isn't explicitly labeled, infer from school context
    - Only say "I don't have information about [X]" if you've thoroughly searched the context and truly cannot find it
    - If you find partial or related information, mention what you found and how it relates
    - Never invent course codes, requirements, or prerequisites
    - Cite sources when making definitive statements (e.g., "According to the Barnard requirements..." or "Based on the Columbia College bulletin...")
    - If context is insufficient, tell the student what information is missing and suggest where they might find it
    
    ## FOR NON-ACADEMIC QUESTIONS:
    If asked something unrelated to academics/college life, give a brief, friendly response, then gently redirect to academic topics.
    {history_text}
    ═══════════════════════════════════════════════════════════
    CONTEXT FROM COURSE BULLETINS, ACADEMIC REQUIREMENTS, AND PROFESSOR REVIEWS:
    ═══════════════════════════════════════════════════════════
    {context_text}
    
    ═══════════════════════════════════════════════════════════
    STUDENT'S QUESTION:
    ═══════════════════════════════════════════════════════════
    {question}
    
    ═══════════════════════════════════════════════════════════
    CRITICAL REMINDERS BEFORE ANSWERING:
    ═══════════════════════════════════════════════════════════
    ✓ What type of question is this? (factual info vs. planning/recommendations vs. professor reviews)
    ✓ Is this related to the previous conversation? (should I use chat history?)
    ✓ Do I have the information needed in the CONTEXT to answer accurately?
    ✓ If about professors: Are there CULPA reviews in the context? Did I provide balanced positive/negative feedback?
    ✓ If about professors: Is the name partial? Should I clarify or suggest similar names?
    ✓ If making recommendations: Have they mentioned courses already taken?
    ✓ If making recommendations: Do I need to ask for more information first?
    
    **Response approach based on question type:**
    - Factual question about courses/requirements -> Answer directly from context
    - Professor review question -> Provide balanced summary with rating, positive/negative points, handle partial names
    - Personalized planning -> Check for completed courses, ask for missing info if needed
    - Follow-up question -> Reference chat history if relevant
    - Unrelated new question -> Ignore chat history, focus on current question
    """)

# -------------------------------
# Comparison Query Detection and Multi-Query Retrieval
# -------------------------------

def detect_professor_comparison(question: str) -> Optional[tuple]:
    """
    Detect if the question is comparing two professors.
    Returns (professor1, professor2) if comparison detected, None otherwise.
    """
    # Patterns to detect comparisons - ordered from most specific to least specific
    patterns = [
        # "Compare Professor X and Professor Y"
        r'compare\s+professor\s+([a-zA-Z\'\-]+(?:\s+[a-zA-Z\'\-]+)?)\s+(?:and|to|with|vs\.?|versus)\s+professor\s+([a-zA-Z\'\-]+(?:\s+[a-zA-Z\'\-]+)?)',
        # "Compare X and Y for..." (without "professor")
        r'compare\s+([a-zA-Z\'\-]+(?:\s+[a-zA-Z\'\-]+)?)\s+(?:and|to|with|vs\.?|versus)\s+([a-zA-Z\'\-]+(?:\s+[a-zA-Z\'\-]+)?)\s+for',
        # "Which is better: Professor X or Professor Y"
        r'(?:which|who)\s+is\s+better[\s\:]+professor\s+([a-zA-Z\'\-]+(?:\s+[a-zA-Z\'\-]+)?)\s+(?:or|vs\.?)\s+professor\s+([a-zA-Z\'\-]+(?:\s+[a-zA-Z\'\-]+)?)',
        # "How does Professor X compare to Professor Y"
        r'how\s+does\s+professor\s+([a-zA-Z\'\-]+(?:\s+[a-zA-Z\'\-]+)?)\s+compare\s+(?:to|with)\s+professor\s+([a-zA-Z\'\-]+(?:\s+[a-zA-Z\'\-]+)?)',
        # "Professor X versus Professor Y"
        r'professor\s+([a-zA-Z\'\-]+(?:\s+[a-zA-Z\'\-]+)?)\s+(?:versus|vs\.?)\s+professor\s+([a-zA-Z\'\-]+(?:\s+[a-zA-Z\'\-]+)?)',
    ]
    
    question_lower = question.lower()
    
    for pattern in patterns:
        match = re.search(pattern, question_lower, re.IGNORECASE)
        if match:
            prof1 = match.group(1).strip()
            prof2 = match.group(2).strip()
            
            # Validate that we got reasonable professor names (2-4 words max)
            prof1_words = prof1.split()
            prof2_words = prof2.split()
            
            if (len(prof1_words) <= 4 and len(prof2_words) <= 4 and 
                prof1 and prof2 and prof1 != prof2):
                return (prof1, prof2)
    
    return None


def retrieve_for_professor(
    professor_name: str,
    embedder: OpenAIEmbeddings,
    cur,
    table_name: str,
    school_filter: Optional[tuple],
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieve chunks specifically for a given professor.
    school_filter is now a tuple: (included_patterns, excluded_patterns)
    """
    # Create a targeted query for this professor
    prof_query = f"Professor {professor_name} teaching style reviews rating"
    prof_vec = embedder.embed_query(prof_query)
    vec_literal = "[" + ",".join(f"{x:.8f}" for x in prof_vec) + "]"
    prof_pattern = f"%{professor_name}%"
    
    # Search specifically for CULPA sources mentioning this professor
    if school_filter:
        included_patterns, excluded_patterns = school_filter
        
        if included_patterns:
            # Build OR conditions for included school sources
            included_conditions = " OR ".join(["source ILIKE %s"] * len(included_patterns))
            sql = f"""
                select
                  id,
                  content,
                  1 - (embedding <=> %s::vector) as similarity,
                  source
                from {table_name}
                where (({included_conditions}) OR source ILIKE 'culpa.info%%')
                  and (content ILIKE %s OR source ILIKE %s)
                order by embedding <=> %s::vector
                limit %s;
            """
            params = [vec_literal] + included_patterns + [prof_pattern, prof_pattern, vec_literal, limit]
            cur.execute(sql, params)
        else:
            # Fallback: just search CULPA
            sql = f"""
                select
                  id,
                  content,
                  1 - (embedding <=> %s::vector) as similarity,
                  source
                from {table_name}
                where source ILIKE 'culpa.info%%'
                  and (content ILIKE %s OR source ILIKE %s)
                order by embedding <=> %s::vector
                limit %s;
            """
            cur.execute(sql, (vec_literal, prof_pattern, prof_pattern, vec_literal, limit))
    else:
        sql = f"""
            select
              id,
              content,
              1 - (embedding <=> %s::vector) as similarity,
              source
            from {table_name}
            where (content ILIKE %s OR source ILIKE %s)
            order by embedding <=> %s::vector
            limit %s;
        """
        cur.execute(sql, (vec_literal, prof_pattern, prof_pattern, vec_literal, limit))
    
    return cur.fetchall()



# ================================================================
# Main query function (async, cache-aware)
# ================================================================
#
# Public: rag_answer(...)
#
# Cache layers, applied in order:
#   L1 Exact response   -> shortcut before any work
#   L2 Query embedding  -> skip OpenAI embeddings call
#   L3 Retrieved chunks -> skip pgvector lookup
#   L4 LLM response     -> skip OpenAI chat completion
#
# All Redis failures fall through to the live path; see backend/core/cache.py.

import asyncio


def _vector_search_sync(
    conn,
    question: str,
    q_vec: List[float],
    profile: Optional[Dict[str, Any]],
    table_name: str,
    probes: int,
) -> List[Dict[str, Any]]:
    """
    Synchronous vector-search block extracted from `rag_answer` so it can be
    invoked from async code via `asyncio.to_thread`. Uses an already-opened
    psycopg2 connection; caller manages conn lifecycle.
    """
    cur = conn.cursor()
    try:
        cur.execute("set ivfflat.probes = %s;", (probes,))
    except Exception:
        pass

    vec_literal = "[" + ",".join(f"{x:.8f}" for x in q_vec) + "]"

    school_value = None
    if profile and isinstance(profile, dict):
        school_value = profile.get("school")
    school_filter = get_school_source_filter(school_value)

    rows: List[Dict[str, Any]] = []

    # Branch 1 -- professor comparison
    comparison = detect_professor_comparison(question)
    if comparison:
        embedder = OpenAIEmbeddings(model=EMBED_MODEL)
        prof1, prof2 = comparison
        per_prof_limit = TOP_K // 2
        prof1_rows = retrieve_for_professor(prof1, embedder, cur, table_name, school_filter, per_prof_limit)
        prof2_rows = retrieve_for_professor(prof2, embedder, cur, table_name, school_filter, per_prof_limit)
        seen_ids = set()
        for row in prof1_rows + prof2_rows:
            if row["id"] not in seen_ids:
                rows.append(row)
                seen_ids.add(row["id"])
        rows = sorted(rows, key=lambda x: x["similarity"], reverse=True)[:TOP_K]
        cur.close()
        return rows

    # Branch 2 -- scoped by school filter
    if school_filter:
        included_patterns, excluded_patterns = school_filter
        if included_patterns:
            included_conditions = " OR ".join(["source ILIKE %s"] * len(included_patterns))
            school_sql = f"""
                select id, content, 1 - (embedding <=> %s::vector) as similarity, source
                from {table_name}
                where (({included_conditions}) OR source ILIKE 'culpa.info%%')
                order by embedding <=> %s::vector
                limit %s;
            """
            params = [vec_literal] + included_patterns + [vec_literal, TOP_K]
            cur.execute(school_sql, params)
        else:
            school_sql = f"""
                select id, content, 1 - (embedding <=> %s::vector) as similarity, source
                from {table_name}
                where source ILIKE 'culpa.info%%'
                order by embedding <=> %s::vector
                limit %s;
            """
            cur.execute(school_sql, (vec_literal, vec_literal, TOP_K))
        rows.extend(cur.fetchall())
        existing_ids = {row["id"] for row in rows}
        if len(rows) < TOP_K:
            remaining = TOP_K - len(rows)
            if excluded_patterns:
                excluded_conditions = " AND ".join(["source NOT ILIKE %s"] * len(excluded_patterns))
                general_sql = f"""
                    select id, content, 1 - (embedding <=> %s::vector) as similarity, source
                    from {table_name}
                    where ({excluded_conditions} OR source ILIKE 'culpa.info%%')
                    order by embedding <=> %s::vector
                    limit %s;
                """
                params = excluded_patterns + [vec_literal, vec_literal, remaining]
                cur.execute(general_sql, params)
            else:
                general_sql = f"""
                    select id, content, 1 - (embedding <=> %s::vector) as similarity, source
                    from {table_name}
                    where source ILIKE 'culpa.info%%'
                    order by embedding <=> %s::vector
                    limit %s;
                """
                cur.execute(general_sql, (vec_literal, vec_literal, remaining))
            for row in cur.fetchall():
                if row["id"] not in existing_ids:
                    rows.append(row)
                    existing_ids.add(row["id"])
                    if len(rows) >= TOP_K:
                        break
        rows = sorted(rows, key=lambda x: x["similarity"], reverse=True)[:TOP_K]
        cur.close()
        return rows

    # Branch 3 -- unfiltered
    base_sql = f"""
        select id, content, 1 - (embedding <=> %s::vector) as similarity, source
        from {table_name}
        order by embedding <=> %s::vector
        limit %s;
    """
    cur.execute(base_sql, (vec_literal, vec_literal, TOP_K))
    rows = cur.fetchall()
    cur.close()
    return rows


async def rag_answer(
    question: str,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    table_name: str = "documents",
    probes: int = 10,
    save_to_db: bool = True,
) -> dict:
    """
    Async, cache-aware RAG pipeline.

    * Never blocks the event loop -- sync I/O (psycopg2, langchain .invoke)
      runs in a thread pool.
    * Redis failures fall through silently to the live path.
    """
    from backend.core import cache as _cache  # local import avoids cycles

    # --- Step 0: connect and hydrate context (profile + history) ------------
    conn = await asyncio.to_thread(get_pg_conn)
    try:
        profile: Optional[Dict[str, Any]] = None
        try:
            if user_id:
                profile = await asyncio.to_thread(get_user_profile, conn, user_id)
        except Exception as e:
            print(f"Warning: Could not fetch user profile: {e}")
            profile = None

        profile_summary = format_profile_summary(profile) if profile else None
        school_value = profile.get("school") if isinstance(profile, dict) else None

        # Conversation: load existing or (optionally) create one.
        is_new_conversation = conversation_id is None
        chat_history: List[Dict[str, Any]] = []
        if conversation_id:
            chat_history = await asyncio.to_thread(
                get_conversation_history, conn, conversation_id, MAX_HISTORY_MESSAGES
            )
        elif save_to_db:
            conversation_id = await asyncio.to_thread(create_conversation, conn, user_id)

        history_len = len(chat_history)

        # --- Step 1: prefetch L1 + L2 + L3 in a single pipeline -------------
        #
        # L1 is skipped on brand-new conversations: a cache hit there would
        # return a payload with a stale conversation_id from a prior session.
        # L2 and L3 are always safe because they're scoped to query-level data.
        prefetched = await _cache.prefetch_layers(
            query=question,
            user_id=user_id,
            conversation_id=None if is_new_conversation else conversation_id,
            profile=profile,
            history_len=history_len,
            school=school_value,
        )

        # --- Step 2: L1 shortcut --------------------------------------------
        if not is_new_conversation and prefetched.get("exact"):
            cached = prefetched["exact"]
            # Overwrite IDs the cache shouldn't own.
            cached["conversation_id"] = conversation_id
            if save_to_db and conversation_id:
                await asyncio.to_thread(save_message, conn, conversation_id, "user", question)
                await asyncio.to_thread(
                    save_message, conn, conversation_id, "assistant",
                    cached.get("answer", ""), {"served_from_cache": "exact"},
                )
            cached["served_from_cache"] = "exact"
            cached["chat_history"] = chat_history
            return cached

        # --- Step 3: embedding (L2) -----------------------------------------
        q_vec: Optional[List[float]] = prefetched.get("embedding")
        if q_vec is None:
            embedder = OpenAIEmbeddings(model=EMBED_MODEL)
            q_vec = await embedder.aembed_query(question)
            await _cache.set_embedding(question, q_vec)

        # --- Step 3a: semantic response cache (L1.5) ------------------------
        if history_len == 0 and q_vec:
            semantic_hit = await _cache.get_semantic_response(
                query=question,
                embedding=q_vec,
                school=school_value,
                profile=profile,
            )
            if semantic_hit is not None:
                semantic_hit["conversation_id"] = conversation_id
                semantic_hit["chat_history"] = chat_history
                semantic_hit["served_from_cache"] = "semantic"
                if save_to_db and conversation_id:
                    await asyncio.to_thread(
                        save_message, conn, conversation_id, "user", question,
                    )
                    await asyncio.to_thread(
                        save_message, conn, conversation_id, "assistant",
                        semantic_hit.get("answer", ""),
                        {"served_from_cache": "semantic"},
                    )
                return semantic_hit

        # --- Step 4: chunks (L3) --------------------------------------------
        rows: List[Dict[str, Any]] = prefetched.get("chunks") or []
        if not rows:
            rows = await asyncio.to_thread(
                _vector_search_sync, conn, question, q_vec, profile, table_name, probes,
            )
            # Only cache if we actually retrieved something -- empty lists usually
            # mean a DB/query failure we don't want to memoize.
            if rows:
                # psycopg2 RealDictRow isn't directly JSON-serializable; coerce.
                serializable = [
                    {
                        "id": r["id"],
                        "content": r["content"],
                        "similarity": float(r["similarity"]),
                        "source": r.get("source"),
                    }
                    for r in rows
                ]
                await _cache.set_chunks(question, school_value, serializable)

        contexts = [row["content"] for row in rows]

        # --- Step 5: LLM answer (L4) ----------------------------------------
        cached_answer = await _cache.get_llm_response(
            question, user_id,
            None if is_new_conversation else conversation_id,
            profile, history_len, rows,
        )
        if cached_answer is not None:
            answer = cached_answer
            gen_model_name = "cache:llm"
        else:
            prompt = build_prompt(question, contexts, chat_history, profile_summary)
            if LLM_PROVIDER == "openai":
                llm = ChatOpenAI(
                    model=OPENAI_MODELS[OPENAI_MODEL], temperature=LLM_TEMPERATURE,
                )
                gen_model_name = f"openai:{OPENAI_MODEL}"
            else:
                llm = ChatOllama(
                    model=OLLAMA_MODELS[OLLAMA_MODEL],
                    base_url="http://localhost:11434",
                    temperature=LLM_TEMPERATURE,
                )
                gen_model_name = f"ollama:{OLLAMA_MODEL}"
            response = await llm.ainvoke(prompt)
            answer = response.content
            await _cache.set_llm_response(
                question, user_id,
                None if is_new_conversation else conversation_id,
                profile, history_len, rows, answer,
            )

        # --- Step 6: persist messages ---------------------------------------
        if save_to_db and conversation_id:
            await asyncio.to_thread(save_message, conn, conversation_id, "user", question)
            metadata = {
                "top_matches": [
                    {
                        "id": r["id"],
                        "similarity": float(r["similarity"]),
                        "content_preview": r["content"][:200],
                    }
                    for r in rows[:5]
                ],
            }
            if profile_summary:
                metadata["student_profile_summary"] = profile_summary
            await asyncio.to_thread(
                save_message, conn, conversation_id, "assistant", answer, metadata,
            )

        # --- Step 7: response + L1 write-back -------------------------------
        response_payload = {
            "conversation_id": conversation_id,
            "question": question,
            "answer": answer,
            "matches": [
                {
                    "id": r["id"],
                    "content": r["content"],
                    "similarity": float(r["similarity"]),
                    "source": r.get("source"),
                }
                for r in rows
            ],
            "chat_history": chat_history,
            "used_model_embed": EMBED_MODEL,
            "used_model_llm": gen_model_name,
        }

        # Only cache L1 for established conversations, to avoid leaking stale
        # conversation_ids between sessions.
        cacheable_payload: Optional[Dict[str, Any]] = None
        if not is_new_conversation:
            cacheable_payload = {k: v for k, v in response_payload.items()
                                 if k not in ("chat_history", "conversation_id")}
            await _cache.set_exact_response(
                question, user_id, conversation_id, profile, history_len, cacheable_payload,
            )

        if history_len == 0 and q_vec:
            if cacheable_payload is None:
                cacheable_payload = {k: v for k, v in response_payload.items()
                                     if k not in ("chat_history", "conversation_id")}
            await _cache.set_semantic_response(
                query=question,
                embedding=q_vec,
                answer=cacheable_payload,
                school=school_value,
                profile=profile,
            )

        return response_payload
    finally:
        try:
            conn.close()
        except Exception:
            pass


# -------------------------------
# CLI usage
# -------------------------------
if __name__ == "__main__":
    print("\n" + "="*80)
    print("AskAlma - Academic Assistant with Conversation Context")
    print("="*80)

    async def _cli_demo() -> None:
        # Example: Start a new conversation
        q1 = "What are the core classes for first year Columbia College students?"
        result1 = await rag_answer(q1, conversation_id=None, save_to_db=True)

        # Example: Continue the conversation with a follow-up question
        print("\n" + "-"*80)
        print("\n--- Follow-up question in SAME conversation ---\n")
        conversation_id = result1['conversation_id']
        q2 = "What are the prerequisites for those classes?"
        result2 = await rag_answer(q2, conversation_id=conversation_id, save_to_db=True)
        print(f"Q: {q2}")
        print(f"\nA: {result2['answer']}")

        # Example: Another follow-up
        print("\n" + "-"*80)
        print("\n--- Another follow-up question ---\n")
        q3 = "How many credits are they worth in total?"
        result3 = await rag_answer(q3, conversation_id=conversation_id, save_to_db=True)
        return result2, result3

    result2, result3 = asyncio.run(_cli_demo())
    
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
        print(f"\n{'-'*80}")
        print(f"[{i}] SIMILARITY: {r['similarity']:.4f} | ID: {r['id']}")
        print(f"{'-'*80}")
        print(r['content'])
        print(f"{'-'*80}")