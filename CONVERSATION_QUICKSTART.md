# Conversation System - Quick Start Guide

## 🚀 What's New

Your RAG system now supports **multi-turn conversations** with context! Users can ask follow-up questions that reference previous messages.

## 📋 Setup (One-Time)

### 1. Run the SQL in Supabase

Open your Supabase SQL Editor and run:

```sql
-- Create conversation tables
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at);
```

See the full SQL in the previous message for triggers and additional features.

### 2. Updated Files

Your `rag_query.py` has been updated with:
- ✅ Conversation history loading
- ✅ Context-aware prompts
- ✅ Automatic message saving
- ✅ Multi-turn conversation support

New files created:
- ✅ `interactive_chat.py` - Easy-to-use chat interface
- ✅ `conversation_utils.py` - Conversation management tools
- ✅ `CONVERSATION_SYSTEM.md` - Full documentation

## 🎯 Quick Usage Examples

### Option 1: Interactive Chat (Recommended for Testing)

```bash
cd src/embedder/embeddings
python3 interactive_chat.py
```

Then just chat naturally:
```
You: What are the core classes for Columbia Engineering?
Assistant: [Detailed answer]

You: What are the prerequisites for those?
Assistant: [Answer that understands "those" refers to core classes]

You: How many credits in total?
Assistant: [Answer with full context]
```

### Option 2: Python Code

```python
from rag_query import rag_answer

# First question - creates new conversation
result = rag_answer("What CS courses require calculus?")
conv_id = result['conversation_id']
print(result['answer'])

# Follow-up - maintains context
result = rag_answer(
    "What are the prerequisites for those courses?",
    conversation_id=conv_id
)
print(result['answer'])

# Another follow-up
result = rag_answer(
    "When are they typically offered?",
    conversation_id=conv_id
)
print(result['answer'])
```

### Option 3: CLI Demo

```bash
cd src/embedder/embeddings
python3 rag_query.py
```

This runs a 3-question conversation demo.

## 🛠️ Managing Conversations

### List all conversations
```bash
python3 conversation_utils.py list
```

### View a conversation
```bash
python3 conversation_utils.py view <conversation-id>
```

### Delete a conversation
```bash
python3 conversation_utils.py delete <conversation-id>
```

## 📊 What Gets Stored

### In `conversations` table:
- Conversation ID (UUID)
- Title (auto-generated from first message)
- Created and updated timestamps

### In `messages` table:
- All user questions
- All assistant responses
- Metadata (retrieved chunks, similarity scores)
- Timestamps

## 🎨 Key Features

### 1. **Automatic Context**
The system automatically includes previous messages in the prompt, so follow-up questions work naturally:

```
You: "What is COMS W3134?"
Assistant: "Data Structures and Algorithms..."

You: "What are its prerequisites?"
# System knows "its" refers to COMS W3134
```

### 2. **Persistent History**
All conversations are saved to the database. You can:
- Resume conversations later
- Review past conversations
- Analyze conversation patterns

### 3. **Smart Retrieval**
Each question still performs semantic search, but now with conversational context:
- Retrieved chunks + chat history = better answers
- Handles pronouns and references ("it", "those", "that class")

## ⚙️ Configuration

In `rag_query.py`, adjust these settings:

```python
TOP_K = 10                    # Number of chunks to retrieve
MAX_CONTEXT_CHARS = 8000      # Max context length
MAX_HISTORY_MESSAGES = 10     # Max messages to include
```

## 🔄 API Reference

### Main Function

```python
rag_answer(
    question: str,                    # User's question
    conversation_id: Optional[str],   # Existing conv ID or None
    table_name: str = "documents",    # Table to search
    probes: int = 10,                 # Search accuracy
    save_to_db: bool = True           # Whether to save
) -> dict
```

### Return Value

```python
{
    "conversation_id": "uuid",
    "question": "user's question",
    "answer": "assistant's response",
    "matches": [...],           # Retrieved chunks
    "chat_history": [...],      # Previous messages
    "used_model_embed": "...",
    "used_model_llm": "..."
}
```

## 💡 Tips

1. **Start Fresh**: Use `conversation_id=None` for unrelated topics
2. **Continue Talking**: Pass the same `conversation_id` for follow-ups
3. **Clean Up**: Periodically delete old conversations
4. **Test First**: Use `interactive_chat.py` to test the system
5. **Monitor Tokens**: Long conversations might hit LLM token limits

## 🐛 Troubleshooting

**"Conversation not found"**
- The conversation_id might be invalid
- Set `conversation_id=None` to start a new one

**"Context too long"**
- Reduce `MAX_HISTORY_MESSAGES` or `MAX_CONTEXT_CHARS`
- Start a new conversation

**Database connection issues**
- Check your `.env` file has `DATABASE_URL`
- Verify Supabase is accessible
- Ensure the SQL tables were created

## 📚 Full Documentation

See `CONVERSATION_SYSTEM.md` for:
- Complete architecture details
- Database schema
- Advanced usage patterns
- API reference
- Future enhancements

## 🎓 Example Conversations

### Academic Planning
```
Q1: "I'm a sophomore studying Computer Engineering. What should I take?"
Q2: "What are the prerequisites for those classes?"
Q3: "Which ones can I take concurrently?"
```

### Course Information
```
Q1: "Tell me about Data Structures"
Q2: "What programming languages does it use?"
Q3: "Is there a lab component?"
```

### Requirement Checking
```
Q1: "What are the Core Curriculum requirements?"
Q2: "Which ones can satisfy multiple requirements?"
Q3: "How many credits total?"
```

## ✨ Next Steps

1. Run the SQL to create tables
2. Test with `python3 interactive_chat.py`
3. Integrate into your application
4. Monitor usage and conversations
5. Consider adding user authentication

---

**Questions?** Check `CONVERSATION_SYSTEM.md` for detailed documentation!

