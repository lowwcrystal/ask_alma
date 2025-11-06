# Conversation System Documentation

## Overview

The AskAlma RAG system now supports **conversation history**, allowing users to have multi-turn conversations where follow-up questions can reference previous context.

## Database Schema

### Tables

#### `conversations`
Stores conversation metadata:
- `id` (UUID): Unique conversation identifier
- `title` (TEXT): Auto-generated from first user message
- `created_at` (TIMESTAMP): When the conversation started
- `updated_at` (TIMESTAMP): Last message timestamp (auto-updated)

#### `messages`
Stores all messages in conversations:
- `id` (UUID): Unique message identifier
- `conversation_id` (UUID): Foreign key to conversations table
- `role` (TEXT): Either 'user', 'assistant', or 'system'
- `content` (TEXT): The message text
- `created_at` (TIMESTAMP): When the message was sent
- `metadata` (JSONB): Additional data (e.g., retrieved chunks, similarity scores)

### Features

1. **Auto-generated titles**: The first user message becomes the conversation title (truncated to 100 chars)
2. **Cascade deletion**: Deleting a conversation automatically deletes all its messages
3. **Efficient indexing**: Indexes on conversation_id and timestamps for fast queries
4. **Metadata storage**: Assistant messages store information about which chunks were retrieved

## Usage

### 1. Interactive Chat (Easiest)

Use the interactive chat interface for testing:

```bash
cd src/embedder/embeddings
python3 interactive_chat.py
```

**Commands:**
- Type any question to ask
- `new` - Start a new conversation
- `history` - View current conversation history
- `exit` or `quit` - Exit the program

**Example session:**
```
🧑 You: What are the core classes for Columbia College?
🤖 Assistant: [Answer...]

🧑 You: What are the prerequisites for those?
🤖 Assistant: [Answer using context from previous question...]

🧑 You: history
📜 CONVERSATION HISTORY
[Shows all previous messages]

🧑 You: new
✨ Starting a new conversation...
```

### 2. Programmatic Usage

#### Start a New Conversation

```python
from rag_query import rag_answer

# First question - creates a new conversation
result = rag_answer(
    question="What are the Computer Science requirements?",
    conversation_id=None,  # None means create new conversation
    save_to_db=True
)

print(result['answer'])
conversation_id = result['conversation_id']  # Save this for follow-ups
```

#### Continue an Existing Conversation

```python
# Follow-up question - uses conversation context
result = rag_answer(
    question="What are the prerequisites for those courses?",
    conversation_id=conversation_id,  # Use the same conversation_id
    save_to_db=True
)

print(result['answer'])
```

#### Query Without Saving (Testing)

```python
# Query without saving to database
result = rag_answer(
    question="Tell me about Physics courses",
    save_to_db=False  # Won't save to database
)
```

### 3. Managing Conversations

Use the conversation utilities script:

```bash
cd src/embedder/embeddings

# List all conversations
python3 conversation_utils.py list

# View a specific conversation
python3 conversation_utils.py view <conversation-id>

# Delete a conversation
python3 conversation_utils.py delete <conversation-id>
```

### 4. Python API for Conversation Management

```python
from conversation_utils import (
    list_all_conversations,
    get_conversation_details,
    delete_conversation
)

# Get list of all conversations
conversations = list_all_conversations(limit=10)
for conv in conversations:
    print(f"{conv['title']}: {conv['message_count']} messages")

# Get full conversation details
details = get_conversation_details(conversation_id)
print(f"Title: {details['conversation']['title']}")
for msg in details['messages']:
    print(f"{msg['role']}: {msg['content']}")

# Delete a conversation
deleted = delete_conversation(conversation_id)
```

## How It Works

### 1. Conversation Flow

```
User asks question
    ↓
[conversation_id provided?]
    ↓ YES              ↓ NO
Load history    Create new conversation
    ↓                   ↓
Embed question using OpenAI
    ↓
Search database for similar chunks
    ↓
Build prompt with:
  - System message
  - Chat history (if exists)
  - Retrieved context chunks
  - Current question
    ↓
Generate answer with LLM (llama3.1)
    ↓
Save user message to database
Save assistant response to database
    ↓
Return answer + conversation_id
```

### 2. Prompt Construction with History

When conversation history exists, the prompt includes previous messages:

```
You are AskAlma, a helpful academic assistant...

CHAT HISTORY:
USER: What are the core classes?
ASSISTANT: The core classes for Columbia College include...

USER: What are the prerequisites?

CONTEXT:
[Retrieved relevant chunks from database]

QUESTION:
What are the prerequisites?

Answer in a concise, well-structured paragraph...
```

### 3. Context Window Management

- **MAX_HISTORY_MESSAGES**: Limits how many previous messages to include (default: 10)
- **MAX_CONTEXT_CHARS**: Truncates retrieved context if too long (default: 8000 chars)
- These prevent exceeding the LLM's token limit

## Return Value Structure

```python
{
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "question": "What are the prerequisites?",
    "answer": "The prerequisites for...",
    "matches": [
        {
            "id": "abc123",
            "content": "Full chunk text...",
            "similarity": 0.8523
        },
        # ... more matches
    ],
    "chat_history": [
        {
            "role": "user",
            "content": "What are the core classes?",
            "created_at": "2025-01-15 10:30:00",
            "metadata": {}
        },
        {
            "role": "assistant",
            "content": "The core classes include...",
            "created_at": "2025-01-15 10:30:05",
            "metadata": {"top_matches": [...]}
        }
    ],
    "used_model_embed": "text-embedding-3-small",
    "used_model_llm": "llama3.1"
}
```

## Example Use Cases

### 1. Multi-Turn Academic Planning

```python
# First question
result1 = rag_answer("I'm a Computer Engineering sophomore. What classes should I take?")
conv_id = result1['conversation_id']

# Follow-up about specific class
result2 = rag_answer("What are the prerequisites for CSEE 3827?", conversation_id=conv_id)

# Follow-up about scheduling
result3 = rag_answer("When is it offered?", conversation_id=conv_id)

# Follow-up about workload
result4 = rag_answer("How many credits is it?", conversation_id=conv_id)
```

### 2. Exploring Prerequisites

```python
# Initial query
result1 = rag_answer("What is Data Structures about?")
conv_id = result1['conversation_id']

# The system remembers "Data Structures" from context
result2 = rag_answer("What are the prerequisites for that course?", conversation_id=conv_id)
result3 = rag_answer("Do I need to take those in a specific order?", conversation_id=conv_id)
```

### 3. Comparing Options

```python
result1 = rag_answer("Tell me about the Physics major at Columbia")
conv_id = result1['conversation_id']

result2 = rag_answer("How does it compare to the Engineering Physics program?", conversation_id=conv_id)
result3 = rag_answer("Which one has more lab requirements?", conversation_id=conv_id)
```

## Configuration

In `rag_query.py`, you can adjust:

```python
# Maximum number of previous messages to include in context
MAX_HISTORY_MESSAGES = 10

# Maximum characters of retrieved context
MAX_CONTEXT_CHARS = 8000

# Number of chunks to retrieve from vector database
TOP_K = 10
```

## Database Queries

### Get all conversations for a user
```sql
SELECT * FROM conversations 
ORDER BY updated_at DESC;
```

### Get message count per conversation
```sql
SELECT 
    c.id,
    c.title,
    COUNT(m.id) as message_count
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
GROUP BY c.id, c.title
ORDER BY c.updated_at DESC;
```

### Get conversations with recent activity
```sql
SELECT * FROM conversations
WHERE updated_at > NOW() - INTERVAL '7 days'
ORDER BY updated_at DESC;
```

### Search within conversation messages
```sql
SELECT 
    c.title,
    m.role,
    m.content,
    m.created_at
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
WHERE m.content ILIKE '%computer science%'
ORDER BY m.created_at DESC;
```

## Best Practices

1. **Conversation Management**
   - Create a new conversation for each distinct topic/session
   - Use the same conversation_id for related follow-up questions
   - Periodically clean up old conversations

2. **Context Length**
   - Adjust MAX_HISTORY_MESSAGES if conversations are very long
   - Monitor LLM token usage to avoid context window limits

3. **Metadata Storage**
   - Use the metadata JSONB field to store additional information
   - Example: similarity scores, chunk IDs, user feedback

4. **Error Handling**
   - Always handle invalid conversation_ids gracefully
   - Check if conversation exists before querying history

## Future Enhancements

Potential improvements to consider:

1. **User Authentication**: Add a `user_id` field to associate conversations with users
2. **Conversation Sharing**: Allow users to share conversation links
3. **Message Editing**: Add ability to edit previous messages
4. **Branching Conversations**: Fork conversations at any point
5. **Search Conversations**: Full-text search across all conversations
6. **Export Conversations**: Export as JSON, PDF, or markdown
7. **Conversation Analytics**: Track popular topics, average conversation length, etc.
8. **Smart Title Generation**: Use LLM to generate better conversation titles

## Troubleshooting

### Conversation not found
```python
# Check if conversation exists before using it
details = get_conversation_details(conversation_id)
if not details:
    print("Conversation not found, starting a new one")
    conversation_id = None
```

### Too much context history
```python
# Reduce the number of historical messages
result = rag_answer(
    question="...",
    conversation_id=conv_id,
    # Temporarily override the global setting
)
# Modify MAX_HISTORY_MESSAGES in rag_query.py for permanent change
```

### Database connection issues
```python
# Verify your DATABASE_URL in .env
# Ensure Supabase is accessible
# Check that tables were created with the provided SQL
```

