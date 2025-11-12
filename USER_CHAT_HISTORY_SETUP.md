# User-Specific Chat History Setup Guide

## Overview
I've implemented user-specific chat history functionality for AskAlma! Now each user will see only their own conversations in the sidebar when logged in.

## What Was Implemented

### 1. **Database Changes**
- Added `user_id` column to the `conversations` table
- Added database indexes for efficient queries
- Migration SQL file created: `add_user_id_migration.sql`

### 2. **Backend API Changes** 
- Updated `/api/chat` endpoint to accept `user_id`
- Updated `/api/conversations` endpoint to filter by `user_id`
- Modified `rag_query.py` to save `user_id` with new conversations

### 3. **Frontend Changes**
- Updated AskAlma component to:
  - Send `user_id` (from Supabase auth) with chat requests
  - Fetch and display user-specific conversations in sidebar
  - Refresh conversations list when new chat is created
  - Show scrollable list of past conversations
- Landing page does NOT fetch conversations (user not logged in)

## Setup Instructions

### Step 1: Run the Database Migration

You need to add the `user_id` column to your database. Run this SQL:

```bash
# Connect to your Supabase database
psql postgresql://postgres.hihmyzlppijfqlxhalbe:Columbia%40CodeCollab@aws-1-us-east-2.pooler.supabase.com:5432/postgres

# Or run the migration file
\i add_user_id_migration.sql
```

**Or manually in Supabase Dashboard:**
1. Go to: https://app.supabase.com/project/hihmyzlppijfqlxhalbe/editor
2. Run this SQL:

```sql
-- Add user_id column to conversations table
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS user_id TEXT;

-- Add index for faster user-specific queries
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Add index for user + updated_at for efficient sorting
CREATE INDEX IF NOT EXISTS idx_conversations_user_updated ON conversations(user_id, updated_at DESC);
```

### Step 2: Test the Implementation

1. **Start the servers:**
```bash
./start_backend.sh
./start_frontend.sh
```

2. **Test the flow:**
   - Go to http://localhost:3000
   - Sign up or log in with a user account
   - Start a conversation - ask a question
   - The conversation should appear in the left sidebar under "Your Chats"
   - Log out and log in with a different user
   - That user should NOT see the first user's conversations
   - Each user should only see their own chats

3. **Landing Page (not logged in):**
   - Go to http://localhost:3000 (not logged in)
   - You can still chat on the landing page
   - But these conversations won't be saved (no user_id)
   - Sidebar won't show (user not logged in)

## How It Works

### When User Sends a Message:
1. Frontend sends request with `user_id` from Supabase auth
2. Backend creates/uses conversation with that `user_id`
3. Conversation is saved in database linked to that user
4. Frontend refreshes conversations list

### When User Logs In:
1. Frontend automatically fetches conversations for that user
2. Only conversations where `user_id` matches are returned
3. Sidebar displays the list of conversations
4. User can click to switch between conversations

### Sidebar Display:
- **Logged in**: Shows "Your Chats" with list of conversations
- **Not logged in** (landing page): Sidebar not shown
- Each conversation shows title and message count
- Active conversation is highlighted

## File Changes Summary

**Backend:**
- `backend/api.py` - Added user_id support to endpoints
- `src/embedder/rag_query.py` - Updated to save user_id with conversations
- `add_user_id_migration.sql` - Database migration script

**Frontend:**
- `frontend/src/components/AskAlma.jsx` - Added conversations list, fetch logic, user_id in requests
- Landing page unchanged (doesn't fetch conversations)

## Future Enhancements

Possible improvements:
- Add ability to load full conversation history when clicking a conversation
- Add delete button for conversations
- Add conversation search/filter
- Show conversation preview/first message
- Add conversation renaming
- Pagination for many conversations

## Troubleshooting

**Conversations not showing:**
- Check that database migration ran successfully
- Verify user_id column exists: `SELECT column_name FROM information_schema.columns WHERE table_name='conversations';`
- Check browser console for errors
- Verify user is logged in (check `user` object in AuthContext)

**Conversations showing for all users:**
- Verify backend is filtering by user_id
- Check API request includes user_id: look in Network tab
- Verify database has user_id populated for new conversations

**Old conversations without user_id:**
- Existing conversations before migration will have `user_id = NULL`
- These won't show for any user
- You can delete them or manually assign user_ids if needed

## Summary

✅ User-specific chat history fully implemented
✅ Backend filters conversations by user  
✅ Frontend displays only user's conversations
✅ Landing page works without authentication
✅ Sidebar shows conversation list when logged in
✅ New conversations automatically appear in sidebar

Just run the database migration and test it out! 🎉


