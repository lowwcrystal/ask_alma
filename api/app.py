"""
Flask API for AskAlma RAG System
Connects React frontend to the conversation-enabled RAG backend
"""

from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
import sys
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import List

# Load .env from src/embedder/.env before importing rag_query
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, 'src', 'embedder', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
else:
    load_dotenv(override=True)

# Add parent directory to path to import rag_query
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.embedder.rag_query import rag_answer, get_conversation_history, get_pg_conn

app = Flask(__name__, static_folder='../frontend/build', static_url_path='')
# Enable CORS for React frontend with explicit origins
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "*"],
        "methods": ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})


def _normalize_string_list(value) -> List[str]:
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


def _serialize_profile(row):
    """Convert database row into JSON-friendly profile payload."""
    if not row:
        return None
    
    # Handle both dict (RealDictCursor) and tuple (regular cursor) formats
    if isinstance(row, dict):
        return {
            'user_id': row.get('user_id'),
            'school': row.get('school'),
            'academic_year': row.get('academic_year'),
            'major': row.get('major'),
            'minors': row.get('minors') or [],
            'classes_taken': row.get('classes_taken') or [],
            'profile_image': row.get('profile_image'),
            'created_at': row.get('created_at').isoformat() if row.get('created_at') else None,
            'updated_at': row.get('updated_at').isoformat() if row.get('updated_at') else None,
        }
    else:
        # Handle tuple format
        columns = ['user_id', 'school', 'academic_year', 'major', 'minors', 'classes_taken', 'profile_image', 'created_at', 'updated_at']
        row_dict = dict(zip(columns, row))
        return {
            'user_id': row_dict.get('user_id'),
            'school': row_dict.get('school'),
            'academic_year': row_dict.get('academic_year'),
            'major': row_dict.get('major'),
            'minors': row_dict.get('minors') or [],
            'classes_taken': row_dict.get('classes_taken') or [],
            'profile_image': row_dict.get('profile_image'),
            'created_at': row_dict.get('created_at').isoformat() if row_dict.get('created_at') else None,
            'updated_at': row_dict.get('updated_at').isoformat() if row_dict.get('updated_at') else None,
        }


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'AskAlma API is running'
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint
    
    Request body:
    {
        "question": "What are the core classes?",
        "conversation_id": "uuid-string" (optional - null for new conversation),
        "user_id": "user-uuid" (optional - Supabase user ID)
    }
    
    Response:
    {
        "conversation_id": "uuid-string",
        "answer": "The core classes include...",
        "sources": [
            {
                "id": "abc123",
                "similarity": 0.85,
                "content": "..."
            }
        ],
        "model": "openai:gpt-4o-mini"
    }
    """
    try:
        data = request.json
        question = data.get('question')
        conversation_id = data.get('conversation_id')  # None for new conversation
        user_id = data.get('user_id')  # Supabase user ID (optional)
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Call the RAG system
        result = rag_answer(
            question=question,
            conversation_id=conversation_id,
            user_id=user_id,
            save_to_db=True
        )
        
        # Format response for frontend
        response = {
            'conversation_id': result['conversation_id'],
            'answer': result['answer'],
            'sources': [
                {
                    'id': match['id'],
                    'similarity': float(match['similarity']),
                    'content': match['content'][:200] + '...'  # Preview only
                }
                for match in result['matches'][:5]  # Top 5 sources
            ],
            'model': result['used_model_llm']
        }
        
        return jsonify(response)
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in /api/chat: {e}")
        print(f"Full traceback:\n{error_trace}")
        return jsonify({'error': str(e), 'traceback': error_trace}), 500


@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """
    Get conversation history
    
    Response:
    {
        "conversation_id": "uuid",
        "messages": [
            {
                "role": "user",
                "content": "What are the core classes?",
                "created_at": "2025-01-15T10:30:00"
            },
            {
                "role": "assistant", 
                "content": "The core classes include...",
                "created_at": "2025-01-15T10:30:05"
            }
        ]
    }
    """
    try:
        conn = get_pg_conn()
        history = get_conversation_history(conn, conversation_id)
        conn.close()
        
        # Format messages for frontend
        messages = [
            {
                'role': msg['role'],
                'content': msg['content'],
                'created_at': msg['created_at'].isoformat() if msg['created_at'] else None
            }
            for msg in history
        ]
        
        return jsonify({
            'conversation_id': conversation_id,
            'messages': messages
        })
    
    except Exception as e:
        print(f"Error in /api/conversations: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/profile/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    """Retrieve the stored academic profile for a Supabase user."""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
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
        """, (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify({'error': 'Profile not found'}), 404

        serialized = _serialize_profile(row)
        if not serialized:
            return jsonify({'error': 'Failed to serialize profile'}), 500

        return jsonify(serialized)

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error fetching profile for user_id={user_id}: {e}")
        print(f"Traceback: {error_trace}")
        return jsonify({'error': str(e), 'traceback': error_trace}), 500


@app.route('/api/profile', methods=['POST', 'PUT'])
def upsert_user_profile():
    """Create or update a user's academic profile details."""
    try:
        data = request.json or {}
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        school = data.get('school')
        academic_year = data.get('academic_year')
        major = data.get('major')
        minors = _normalize_string_list(data.get('minors'))
        classes_taken = _normalize_string_list(data.get('classes_taken'))
        profile_image = data.get('profile_image')

        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("""
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
        """, (user_id, school, academic_year, major, minors, classes_taken, profile_image))
        profile = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        return jsonify(_serialize_profile(profile))

    except Exception as e:
        print(f"Error saving profile for user_id={data.get('user_id')}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    """
    List recent conversations for a specific user
    
    Query Parameters:
        user_id: (optional) Supabase user ID to filter conversations
    
    Response:
    {
        "conversations": [
            {
                "id": "uuid",
                "title": "What are the core classes?",
                "updated_at": "2025-01-15T10:30:00",
                "message_count": 6
            }
        ]
    }
    """
    try:
        user_id = request.args.get('user_id')  # Get user_id from query params
        print(f"Fetching conversations for user_id: {user_id}")
        
        conn = get_pg_conn()
        print(f"Database connection established: {conn is not None}")
        cur = conn.cursor()
        
        # Filter by user_id if provided
        if user_id:
            cur.execute("""
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
            """, (user_id,))
        else:
            # No user_id provided - return all conversations (for backwards compatibility)
            cur.execute("""
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
            """)
        
        conversations = cur.fetchall()
        print(f"Found {len(conversations)} conversations")
        cur.close()
        conn.close()
        
        # Format for frontend
        result = [
            {
                'id': str(conv['id']),
                'title': conv['title'] or 'Untitled Conversation',
                'updated_at': conv['updated_at'].isoformat() if conv['updated_at'] else None,
                'message_count': conv['message_count']
            }
            for conv in conversations
        ]
        
        return jsonify({'conversations': result})
    
    except Exception as e:
        import traceback
        print(f"Error in /api/conversations: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to fetch conversations: {str(e)}'}), 500


@app.route('/api/conversations/search', methods=['GET'])
def search_conversations():
    """
    Search conversations by title or message content
    
    Query Parameters:
        user_id: Supabase user ID to filter conversations
        query: Search query string
    
    Response:
    {
        "conversations": [
            {
                "id": "uuid",
                "title": "What are the core classes?",
                "updated_at": "2025-01-15T10:30:00",
                "message_count": 6
            }
        ]
    }
    """
    try:
        user_id = request.args.get('user_id')
        search_query = request.args.get('query', '').strip()
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        if not search_query:
            return jsonify({'conversations': []}), 200
        
        conn = get_pg_conn()
        cur = conn.cursor()
        
        # Search in both conversation titles and message content
        # Use ILIKE for case-insensitive search
        search_pattern = f'%{search_query}%'
        
        cur.execute("""
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
        """, (user_id, search_pattern, search_pattern))
        
        conversations = cur.fetchall()
        cur.close()
        conn.close()
        
        # Format for frontend
        result = [
            {
                'id': str(conv['id']),
                'title': conv['title'] or 'Untitled Conversation',
                'updated_at': conv['updated_at'].isoformat() if conv['updated_at'] else None,
                'message_count': conv['message_count']
            }
            for conv in conversations
        ]
        
        return jsonify({'conversations': result})
    
    except Exception as e:
        import traceback
        print(f"Error in /api/conversations/search: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to search conversations: {str(e)}'}), 500


@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM conversations WHERE id = %s;", (conversation_id,))
        conn.commit()
        
        deleted = cur.rowcount > 0
        cur.close()
        conn.close()
        
        if deleted:
            return jsonify({'success': True, 'message': 'Conversation deleted'})
        else:
            return jsonify({'error': 'Conversation not found'}), 404
    
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<conversation_id>', methods=['PATCH'])
def update_conversation(conversation_id):
    """Update a conversation (e.g., rename)"""
    try:
        data = request.json
        title = data.get('title')
        
        if not title or not title.strip():
            return jsonify({'error': 'Title is required'}), 400
        
        conn = get_pg_conn()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE conversations 
            SET title = %s
            WHERE id = %s
            RETURNING id, title;
        """, (title.strip(), conversation_id))
        
        updated = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if updated:
            return jsonify({
                'success': True,
                'conversation': {
                    'id': updated['id'],
                    'title': updated['title']
                }
            })
        else:
            return jsonify({'error': 'Conversation not found'}), 404
    
    except Exception as e:
        print(f"Error updating conversation: {e}")
        return jsonify({'error': str(e)}), 500


# Serve React App (catch-all route must be last)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve React frontend with optimized caching"""
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        response = send_from_directory(app.static_folder, path)
        
        # Add cache headers for static assets
        if path.endswith(('.js', '.css', '.png', '.jpg', '.jpeg', '.svg', '.ico', '.woff', '.woff2')):
            # Cache static assets for 1 year (with versioning in filename)
            response.cache_control.max_age = 31536000
            response.cache_control.public = True
            response.cache_control.immutable = True
        elif path.endswith('.html'):
            # Don't cache HTML files
            response.cache_control.no_cache = True
            response.cache_control.no_store = True
            response.cache_control.must_revalidate = True
        
        return response
    else:
        # Don't cache index.html
        response = send_from_directory(app.static_folder, 'index.html')
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True
        return response


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎓 AskAlma API Server Starting...")
    print("="*60)
    print("📍 API will be available at: http://localhost:5001")
    print("📡 Endpoints:")
    print("   GET    /api/health")
    print("   POST   /api/chat")
    print("   GET    /api/conversations")
    print("   GET    /api/conversations/<id>")
    print("   PATCH  /api/conversations/<id>")
    print("   DELETE /api/conversations/<id>")
    print("   GET    /api/profile/<user_id>")
    print("   POST   /api/profile")
    print("="*60 + "\n")
    
    # Run the Flask server (port 5001 to avoid conflict with macOS AirPlay)
    app.run(debug=True, host='0.0.0.0', port=5001)

