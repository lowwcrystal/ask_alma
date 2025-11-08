# AskAlma Frontend-Backend Integration Guide

## 🎯 Overview

Your AskAlma system now has:
- ✅ **Backend**: Python RAG system with conversation history (Flask API)
- ✅ **Frontend**: React chat interface
- ✅ **Connected**: Real-time AI responses with context

## 🚀 Quick Start (First Time)

### 1. Install Backend Dependencies

```bash
cd /Users/henriquesampaio/AskAlma/ask_alma
python3 -m pip install --user -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd /Users/henriquesampaio/AskAlma/ask_alma/frontend
npm install
```

### 3. Verify Environment Variables

Make sure `/Users/henriquesampaio/AskAlma/ask_alma/src/embedder/.env` exists with:

```env
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql://user:password@host:port/database
```

## 🎬 Running the Application

You need **TWO terminal windows** open simultaneously:

### Terminal 1: Start Backend API

```bash
cd /Users/henriquesampaio/AskAlma/ask_alma
./start_backend.sh
```

Or manually:
```bash
python3 backend/api.py
```

**Backend will run on**: `http://localhost:5000`

### Terminal 2: Start Frontend

```bash
cd /Users/henriquesampaio/AskAlma/ask_alma
./start_frontend.sh
```

Or manually:
```bash
cd frontend
npm start
```

**Frontend will run on**: `http://localhost:3000`

## 🎨 Using the Application

1. **Open browser**: Navigate to `http://localhost:3000`
2. **Ask a question**: Type in the chat box and press Enter
3. **View AI response**: Real AI answers from your RAG system!
4. **See sources**: Click "Show sources" to see which documents were used
5. **Continue conversation**: Follow-up questions maintain context
6. **Start new chat**: Click "+ New Chat" to start fresh

## 🔧 How It Works

```
┌─────────────────────────────────────────────────────┐
│                React Frontend (Port 3000)            │
│  - User types question                              │
│  - Sends POST to /api/chat                          │
│  - Displays AI response                             │
└──────────────────┬──────────────────────────────────┘
                   │
                   │ HTTP POST
                   ▼
┌─────────────────────────────────────────────────────┐
│              Flask API (Port 5000)                   │
│  - Receives question                                │
│  - Calls rag_answer()                               │
│  - Returns answer + sources                         │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│              RAG System (src/embedder/)              │
│  - Embeds question (OpenAI)                         │
│  - Searches vectors (Supabase)                      │
│  - Generates answer (GPT-4o-mini)                   │
│  - Saves to conversation history                    │
└─────────────────────────────────────────────────────┘
```

## 📡 API Endpoints

### POST `/api/chat`
Send a message and get AI response

**Request:**
```json
{
  "question": "What are the core classes?",
  "conversation_id": "uuid-or-null"
}
```

**Response:**
```json
{
  "conversation_id": "550e8400-...",
  "answer": "The core classes for Columbia College include...",
  "sources": [
    {
      "id": "abc123",
      "similarity": 0.85,
      "content": "Course content preview..."
    }
  ],
  "model": "openai:gpt-4o-mini"
}
```

### GET `/api/conversations`
List all conversations

### GET `/api/conversations/<id>`
Get specific conversation history

### DELETE `/api/conversations/<id>`
Delete a conversation

## 🎛️ Configuration

### Backend Configuration

Edit `src/embedder/rag_query.py`:

```python
# Choose LLM provider
LLM_PROVIDER = "openai"  # or "ollama"

# Choose OpenAI model
OPENAI_MODEL = "gpt-4o-mini"  # or "gpt-4o", "gpt-3.5-turbo"

# Adjust retrieval
TOP_K = 10  # Number of chunks to retrieve
```

### Frontend Configuration

Edit `frontend/src/components/AskAlma.jsx`:

```javascript
// Change API URL if needed
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
```

Or create `frontend/.env`:
```env
REACT_APP_API_URL=http://localhost:5000
```

## 🐛 Troubleshooting

### Backend won't start

**Error: "DATABASE_URL not set"**
- Solution: Create `src/embedder/.env` with your credentials

**Error: "Module not found"**
- Solution: `python3 -m pip install --user -r requirements.txt`

**Error: "Port 5000 already in use"**
- Solution: Kill the process or change port in `backend/api.py`

### Frontend won't connect

**Error: "API error: Failed to fetch"**
- Check if backend is running on `http://localhost:5000`
- Check `http://localhost:5000/api/health` in browser
- Disable any VPN or firewall blocking localhost

**Error: "CORS error"**
- Flask-CORS should be installed (`pip install flask-cors`)
- Check `backend/api.py` has `CORS(app)`

### No AI responses

**Check backend logs** for errors in Terminal 1

**Common issues:**
- OpenAI API key not set or invalid
- Database connection failed
- Embeddings not uploaded to Supabase

## 📊 Features

### ✅ Currently Working

- Real-time AI chat responses
- Conversation history (maintains context)
- Source citations (show which documents were used)
- Multiple conversations
- New chat functionality
- Error handling and loading states

### 🔮 Future Enhancements

- Conversation sidebar with history
- User authentication
- Conversation search
- Export conversations
- Voice input
- Mobile responsive design
- Dark mode

## 🎓 Example Conversation

```
You: What are the core classes for Columbia College?

Alma: The Core Curriculum for Columbia College consists of...
[Shows sources with similarity scores]

You: What are the prerequisites for Literature Humanities?

Alma: For Literature Humanities (Lit Hum), the prerequisites are...
[Remembers we're talking about Core classes]

You: When is it typically offered?

Alma: Literature Humanities is typically offered...
[Understands "it" refers to Lit Hum]
```

## 💡 Tips

1. **Keep both terminals open** while using the app
2. **Watch the backend logs** to see what's happening
3. **Start new chats** for unrelated topics
4. **Use suggested questions** to test the system
5. **Check sources** to verify information accuracy

## 🔗 Related Files

- **Backend API**: `backend/api.py`
- **RAG System**: `src/embedder/rag_query.py`
- **Frontend Chat**: `frontend/src/components/AskAlma.jsx`
- **Environment**: `src/embedder/.env`

## 📞 Need Help?

If something isn't working:
1. Check both terminal windows for error messages
2. Verify `.env` file has correct credentials
3. Test backend API directly: `http://localhost:5000/api/health`
4. Make sure embeddings are in Supabase
5. Try restarting both frontend and backend

---

**Enjoy your AI-powered academic assistant!** 🎓✨

