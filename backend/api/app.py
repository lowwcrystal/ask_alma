"""
FastAPI application for AskAlma RAG System.
Connects React frontend to the conversation-enabled RAG backend.
"""

import sys
import traceback
from pathlib import Path
from typing import Any, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Resolve repo root (backend/api/app.py -> repo root) and load .env before
# importing anything that reads env vars at import time.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
for _candidate in (
    REPO_ROOT / ".env",
    REPO_ROOT / "backend" / "scripts" / "embedder" / ".env",
):
    if _candidate.exists():
        load_dotenv(_candidate, override=True)
        break
else:
    load_dotenv(override=True)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.services.rag_query import (  # noqa: E402
    get_conversation_history,
    get_pg_conn,
    rag_answer,
)

BUILD_DIR = REPO_ROOT / "frontend" / "build"

app = FastAPI(title="AskAlma API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def _normalize_string_list(value: Any) -> List[str]:
    """
    Coerce incoming value into a clean list of non-empty strings.
    Supports comma-separated strings, iterables, or None.
    """
    if value is None:
        return []
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        return [part for part in parts if part]
    if isinstance(value, (list, tuple, set)):
        cleaned = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned
    text = str(value).strip()
    return [text] if text else []


def _serialize_profile(row: Any) -> Optional[dict]:
    """Convert database row into JSON-friendly profile payload."""
    if not row:
        return None

    if isinstance(row, dict):
        return {
            "user_id": row.get("user_id"),
            "school": row.get("school"),
            "academic_year": row.get("academic_year"),
            "major": row.get("major"),
            "minors": row.get("minors") or [],
            "classes_taken": row.get("classes_taken") or [],
            "profile_image": row.get("profile_image"),
            "created_at": row.get("created_at").isoformat()
            if row.get("created_at")
            else None,
            "updated_at": row.get("updated_at").isoformat()
            if row.get("updated_at")
            else None,
        }
    columns = [
        "user_id",
        "school",
        "academic_year",
        "major",
        "minors",
        "classes_taken",
        "profile_image",
        "created_at",
        "updated_at",
    ]
    row_dict = dict(zip(columns, row))
    return {
        "user_id": row_dict.get("user_id"),
        "school": row_dict.get("school"),
        "academic_year": row_dict.get("academic_year"),
        "major": row_dict.get("major"),
        "minors": row_dict.get("minors") or [],
        "classes_taken": row_dict.get("classes_taken") or [],
        "profile_image": row_dict.get("profile_image"),
        "created_at": row_dict.get("created_at").isoformat()
        if row_dict.get("created_at")
        else None,
        "updated_at": row_dict.get("updated_at").isoformat()
        if row_dict.get("updated_at")
        else None,
    }


def _safe_file_under_build(rel_path: str) -> Optional[Path]:
    """Resolve rel_path under BUILD_DIR; return path if it is a file, else None."""
    if not rel_path or ".." in rel_path:
        return None
    candidate = (BUILD_DIR / rel_path).resolve()
    try:
        candidate.relative_to(BUILD_DIR.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _cache_control_for_asset(path: str) -> str:
    if path.endswith(
        (".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2")
    ):
        return "public, max-age=31536000, immutable"
    if path.endswith(".html"):
        return "no-cache, no-store, must-revalidate"
    return ""


class ChatBody(BaseModel):
    question: Optional[str] = None
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None


class ProfileUpsertBody(BaseModel):
    user_id: str
    school: Optional[str] = None
    academic_year: Optional[str] = None
    major: Optional[str] = None
    minors: Optional[Any] = None
    classes_taken: Optional[Any] = None
    profile_image: Optional[str] = None


class ConversationPatchBody(BaseModel):
    title: Optional[str] = None


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "AskAlma API is running"}


@app.post("/api/chat")
def chat(body: ChatBody):
    """Main chat endpoint (RAG)."""
    try:
        question = body.question
        if not question:
            return JSONResponse(
                status_code=400, content={"error": "Question is required"}
            )

        result = rag_answer(
            question=question,
            conversation_id=body.conversation_id,
            user_id=body.user_id,
            save_to_db=True,
        )

        return {
            "conversation_id": result["conversation_id"],
            "answer": result["answer"],
            "sources": [
                {
                    "id": match["id"],
                    "similarity": float(match["similarity"]),
                    "content": match["content"][:200] + "...",
                }
                for match in result["matches"][:5]
            ],
            "model": result["used_model_llm"],
        }
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in /api/chat: {e}")
        print(f"Full traceback:\n{error_trace}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "traceback": error_trace},
        )


@app.get("/api/profile/{user_id}")
def get_user_profile(user_id: str):
    """Retrieve the stored academic profile for a Supabase user."""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT user_id,
                   school,
                   academic_year,
                   major,
                   minors,
                   classes_taken,
                   profile_image,
                   created_at,
                   updated_at
            FROM user_profiles
            WHERE user_id = %s;
            """,
            (user_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return JSONResponse(status_code=404, content={"error": "Profile not found"})

        serialized = _serialize_profile(row)
        if not serialized:
            return JSONResponse(
                status_code=500, content={"error": "Failed to serialize profile"}
            )

        return serialized
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error fetching profile for user_id={user_id}: {e}")
        print(f"Traceback: {error_trace}")
        return JSONResponse(
            status_code=500, content={"error": str(e), "traceback": error_trace},
        )


@app.post("/api/profile")
@app.put("/api/profile")
def upsert_user_profile(body: ProfileUpsertBody):
    """Create or update a user's academic profile details."""
    try:
        if not body.user_id:
            return JSONResponse(
                status_code=400, content={"error": "user_id is required"}
            )

        minors = _normalize_string_list(body.minors)
        classes_taken = _normalize_string_list(body.classes_taken)

        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO user_profiles (user_id, school, academic_year, major, minors, classes_taken, profile_image)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET
                school = EXCLUDED.school,
                academic_year = EXCLUDED.academic_year,
                major = EXCLUDED.major,
                minors = EXCLUDED.minors,
                classes_taken = EXCLUDED.classes_taken,
                profile_image = EXCLUDED.profile_image,
                updated_at = NOW()
            RETURNING user_id, school, academic_year, major, minors, classes_taken, profile_image, created_at, updated_at;
            """,
            (
                body.user_id,
                body.school,
                body.academic_year,
                body.major,
                minors,
                classes_taken,
                body.profile_image,
            ),
        )
        profile = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        return _serialize_profile(profile)
    except Exception as e:
        print(f"Error saving profile for user_id={body.user_id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/conversations")
def list_conversations(user_id: Optional[str] = Query(None)):
    """List recent conversations for a specific user."""
    try:
        print(f"Fetching conversations for user_id: {user_id}")

        conn = get_pg_conn()
        print(f"Database connection established: {conn is not None}")
        cur = conn.cursor()

        if user_id:
            cur.execute(
                """
                SELECT
                    c.id,
                    c.title,
                    c.updated_at,
                    COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = %s
                GROUP BY c.id, c.title, c.updated_at
                ORDER BY c.updated_at DESC
                LIMIT 20;
                """,
                (user_id,),
            )
        else:
            cur.execute(
                """
                SELECT
                    c.id,
                    c.title,
                    c.updated_at,
                    COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                GROUP BY c.id, c.title, c.updated_at
                ORDER BY c.updated_at DESC
                LIMIT 20;
                """
            )

        conversations = cur.fetchall()
        print(f"Found {len(conversations)} conversations")
        cur.close()
        conn.close()

        result = [
            {
                "id": str(conv["id"]),
                "title": conv["title"] or "Untitled Conversation",
                "updated_at": conv["updated_at"].isoformat()
                if conv["updated_at"]
                else None,
                "message_count": conv["message_count"],
            }
            for conv in conversations
        ]

        return {"conversations": result}
    except Exception as e:
        print(f"Error in /api/conversations: {e}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to fetch conversations: {str(e)}"},
        )


@app.get("/api/conversations/search")
def search_conversations(
    user_id: Optional[str] = Query(None),
    q: str = Query("", alias="query"),
):
    """Search conversations by title or message content."""
    try:
        search_query = (q or "").strip()

        if not user_id:
            return JSONResponse(
                status_code=400, content={"error": "user_id is required"}
            )

        if not search_query:
            return {"conversations": []}

        conn = get_pg_conn()
        cur = conn.cursor()

        search_pattern = f"%{search_query}%"

        cur.execute(
            """
            SELECT DISTINCT
                c.id,
                c.title,
                c.updated_at,
                COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.user_id = %s
                AND (
                    c.title ILIKE %s
                    OR m.content ILIKE %s
                )
            GROUP BY c.id, c.title, c.updated_at
            ORDER BY c.updated_at DESC
            LIMIT 50;
            """,
            (user_id, search_pattern, search_pattern),
        )

        conversations = cur.fetchall()
        cur.close()
        conn.close()

        result = [
            {
                "id": str(conv["id"]),
                "title": conv["title"] or "Untitled Conversation",
                "updated_at": conv["updated_at"].isoformat()
                if conv["updated_at"]
                else None,
                "message_count": conv["message_count"],
            }
            for conv in conversations
        ]

        return {"conversations": result}
    except Exception as e:
        print(f"Error in /api/conversations/search: {e}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to search conversations: {str(e)}"},
        )


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    """Get conversation history."""
    try:
        conn = get_pg_conn()
        history = get_conversation_history(conn, conversation_id)
        conn.close()

        messages = [
            {
                "role": msg["role"],
                "content": msg["content"],
                "created_at": msg["created_at"].isoformat()
                if msg["created_at"]
                else None,
            }
            for msg in history
        ]

        return {"conversation_id": conversation_id, "messages": messages}
    except Exception as e:
        print(f"Error in /api/conversations: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM conversations WHERE id = %s;", (conversation_id,))
        conn.commit()

        deleted = cur.rowcount > 0
        cur.close()
        conn.close()

        if deleted:
            return {"success": True, "message": "Conversation deleted"}
        return JSONResponse(status_code=404, content={"error": "Conversation not found"})
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.patch("/api/conversations/{conversation_id}")
def update_conversation(conversation_id: str, body: ConversationPatchBody):
    """Update a conversation (e.g., rename)."""
    try:
        title = body.title

        if not title or not title.strip():
            return JSONResponse(status_code=400, content={"error": "Title is required"})

        conn = get_pg_conn()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE conversations
            SET title = %s
            WHERE id = %s
            RETURNING id, title;
            """,
            (title.strip(), conversation_id),
        )

        updated = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if updated:
            return {
                "success": True,
                "conversation": {"id": updated["id"], "title": updated["title"]},
            }
        return JSONResponse(status_code=404, content={"error": "Conversation not found"})
    except Exception as e:
        print(f"Error updating conversation: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    """Serve React production build with caching similar to the previous Flask setup."""
    if full_path.startswith("api"):
        raise HTTPException(status_code=404, detail="Not found")

    if not BUILD_DIR.is_dir():
        raise HTTPException(
            status_code=503,
            detail="Frontend build not found. Run the frontend build first.",
        )

    if full_path:
        file_path = _safe_file_under_build(full_path)
        if file_path is not None:
            cc = _cache_control_for_asset(full_path)
            headers = {"Cache-Control": cc} if cc else {}
            return FileResponse(file_path, headers=headers)

    index_path = BUILD_DIR / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=503, detail="index.html not found in frontend build.")

    return FileResponse(
        index_path,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("🎓 AskAlma API Server Starting (FastAPI + Uvicorn)...")
    print("=" * 60)
    print("📍 API will be available at: http://localhost:5001")
    print("📡 Endpoints:")
    print("   GET    /api/health")
    print("   POST   /api/chat")
    print("   GET    /api/conversations")
    print("   GET    /api/conversations/search")
    print("   GET    /api/conversations/<id>")
    print("   PATCH  /api/conversations/<id>")
    print("   DELETE /api/conversations/<id>")
    print("   GET    /api/profile/<user_id>")
    print("   POST   /api/profile")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=5001)
