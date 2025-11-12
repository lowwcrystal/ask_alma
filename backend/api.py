"""
Flask API for AskAlma RAG System
Connects React frontend to the conversation-enabled RAG backend
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from dotenv import load_dotenv

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

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

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
        "conversation_id": "uuid-string" (optional - null for new conversation)
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
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Call the RAG system
        result = rag_answer(
            question=question,
            conversation_id=conversation_id,
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
        print(f"Error in /api/chat: {e}")
        return jsonify({'error': str(e)}), 500


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


@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    """
    List recent conversations
    
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
        conn = get_pg_conn()
        cur = conn.cursor()
        
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
        print(f"Error in /api/conversations: {e}")
        return jsonify({'error': str(e)}), 500


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


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🎓 AskAlma API Server Starting...")
    print("="*60)
    print("📍 API will be available at: http://localhost:5001")
    print("📡 Endpoints:")
    print("   GET  /api/health")
    print("   POST /api/chat")
    print("   GET  /api/conversations")
    print("   GET  /api/conversations/<id>")
    print("   DELETE /api/conversations/<id>")
    print("="*60 + "\n")
    
    # Run the Flask server (port 5001 to avoid conflict with macOS AirPlay)
    app.run(debug=True, host='0.0.0.0', port=5001)

