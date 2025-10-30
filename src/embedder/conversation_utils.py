#!/usr/bin/env python3
"""
Utility functions for managing conversations in the AskAlma RAG system.
"""

from rag_query import get_pg_conn
from typing import List, Dict, Any
import sys


def list_all_conversations(limit: int = 20) -> List[Dict[str, Any]]:
    """List all conversations with their titles and message counts."""
    conn = get_pg_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            c.id,
            c.title,
            c.created_at,
            c.updated_at,
            COUNT(m.id) as message_count,
            MAX(m.created_at) as last_message_at
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        GROUP BY c.id, c.title, c.created_at, c.updated_at
        ORDER BY c.updated_at DESC
        LIMIT %s;
    """, (limit,))
    
    conversations = cur.fetchall()
    cur.close()
    conn.close()
    
    return conversations


def get_conversation_details(conversation_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific conversation."""
    conn = get_pg_conn()
    cur = conn.cursor()
    
    # Get conversation metadata
    cur.execute("""
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE id = %s;
    """, (conversation_id,))
    
    conversation = cur.fetchone()
    
    if not conversation:
        cur.close()
        conn.close()
        return None
    
    # Get all messages
    cur.execute("""
        SELECT role, content, created_at, metadata
        FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at ASC;
    """, (conversation_id,))
    
    messages = cur.fetchall()
    cur.close()
    conn.close()
    
    return {
        "conversation": conversation,
        "messages": messages
    }


def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation and all its messages."""
    conn = get_pg_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM conversations WHERE id = %s;", (conversation_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        conn.close()
        return deleted
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        print(f"Error deleting conversation: {e}")
        return False


def print_conversations_list():
    """Print a formatted list of all conversations."""
    conversations = list_all_conversations()
    
    if not conversations:
        print("\n📭 No conversations found.")
        return
    
    print("\n" + "="*80)
    print("💬 ALL CONVERSATIONS")
    print("="*80)
    
    for i, conv in enumerate(conversations, 1):
        title = conv['title'] or "(No title)"
        message_count = conv['message_count']
        updated = conv['updated_at'].strftime("%Y-%m-%d %H:%M")
        
        print(f"\n[{i}] {title[:60]}")
        print(f"    ID: {conv['id']}")
        print(f"    Messages: {message_count} | Last updated: {updated}")
        print("─"*80)


def print_conversation_details(conversation_id: str):
    """Print detailed view of a conversation."""
    details = get_conversation_details(conversation_id)
    
    if not details:
        print(f"\n❌ Conversation {conversation_id} not found.")
        return
    
    conv = details['conversation']
    messages = details['messages']
    
    print("\n" + "="*80)
    print(f"💬 CONVERSATION: {conv['title'] or '(No title)'}")
    print("="*80)
    print(f"ID: {conv['id']}")
    print(f"Created: {conv['created_at'].strftime('%Y-%m-%d %H:%M')}")
    print(f"Messages: {len(messages)}")
    print("="*80 + "\n")
    
    for msg in messages:
        icon = "🧑" if msg['role'] == 'user' else "🤖"
        timestamp = msg['created_at'].strftime("%H:%M:%S")
        
        print(f"{icon} {msg['role'].upper()} [{timestamp}]:")
        print(msg['content'])
        print("─"*80 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python3 conversation_utils.py list              # List all conversations")
        print("  python3 conversation_utils.py view <conv_id>    # View conversation details")
        print("  python3 conversation_utils.py delete <conv_id>  # Delete a conversation")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        print_conversations_list()
    
    elif command == "view":
        if len(sys.argv) < 3:
            print("❌ Error: Please provide a conversation ID")
            sys.exit(1)
        print_conversation_details(sys.argv[2])
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Error: Please provide a conversation ID")
            sys.exit(1)
        
        conv_id = sys.argv[2]
        confirm = input(f"⚠️  Are you sure you want to delete conversation {conv_id}? (yes/no): ")
        
        if confirm.lower() == 'yes':
            if delete_conversation(conv_id):
                print(f"✅ Conversation {conv_id} deleted successfully.")
            else:
                print(f"❌ Failed to delete conversation {conv_id}.")
        else:
            print("❌ Deletion cancelled.")
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)

