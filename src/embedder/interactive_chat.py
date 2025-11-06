#!/usr/bin/env python3
"""
Interactive chat interface for AskAlma RAG system with conversation history.
Run: python3 interactive_chat.py
"""

from rag_query import (
    rag_answer, 
    get_pg_conn, 
    get_conversation_history,
    LLM_PROVIDER,
    OPENAI_MODEL,
    OLLAMA_MODEL
)
import sys

def print_header():
    # Determine which model is being used
    if LLM_PROVIDER == "openai":
        model_info = f"OpenAI {OPENAI_MODEL}"
    else:
        model_info = f"Ollama {OLLAMA_MODEL}"
    
    print("\n" + "="*80)
    print("🎓 AskAlma - Interactive Academic Assistant")
    print("="*80)
    print(f"🤖 Using: {model_info}")
    print("📚 Sources: Columbia College, Columbia Engineering, Barnard")
    print("─"*80)
    print("Commands:")
    print("  'new'     - Start a new conversation")
    print("  'history' - View conversation history")
    print("  'exit'    - Exit the program")
    print("="*80 + "\n")


def print_answer(result):
    print("\n🤖 Assistant:")
    print("─"*80)
    print(result['answer'])
    print("─"*80)
    print(f"\n💡 Retrieved {len(result['matches'])} relevant chunks")
    print(f"📝 Conversation ID: {result['conversation_id']}")


def show_history(conversation_id):
    if not conversation_id:
        print("\n⚠️  No active conversation yet. Ask a question to start one!")
        return
    
    conn = get_pg_conn()
    history = get_conversation_history(conn, conversation_id)
    conn.close()
    
    print("\n" + "="*80)
    print("📜 CONVERSATION HISTORY")
    print("="*80)
    
    if not history:
        print("No messages yet.")
    else:
        for msg in history:
            icon = "🧑" if msg['role'] == 'user' else "🤖"
            print(f"\n{icon} {msg['role'].upper()}:")
            print(f"{msg['content']}")
            print("─"*40)
    
    print()


def main():
    print_header()
    
    conversation_id = None
    
    while True:
        try:
            # Get user input
            user_input = input("\n🧑 You: ").strip()
            
            # Handle commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Thanks for using AskAlma! Goodbye!")
                sys.exit(0)
            
            elif user_input.lower() == 'new':
                conversation_id = None
                print("\n✨ Starting a new conversation...")
                continue
            
            elif user_input.lower() == 'history':
                show_history(conversation_id)
                continue
            
            elif not user_input:
                print("⚠️  Please enter a question.")
                continue
            
            # Process the question
            print("\n⏳ Thinking...")
            result = rag_answer(
                question=user_input,
                conversation_id=conversation_id,
                save_to_db=True
            )
            
            # Update conversation_id if this was the first message
            if not conversation_id:
                conversation_id = result['conversation_id']
                print(f"✨ New conversation started: {conversation_id}")
            
            # Print the answer
            print_answer(result)
            
        except KeyboardInterrupt:
            print("\n\n👋 Thanks for using AskAlma! Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or type 'exit' to quit.")


if __name__ == "__main__":
    main()

