-- Migration: Add user_id to conversations table
-- This allows linking conversations to specific Supabase users

-- Add user_id column to conversations table
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS user_id TEXT;

-- Add index for faster user-specific queries
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Add index for user + updated_at for efficient sorting
CREATE INDEX IF NOT EXISTS idx_conversations_user_updated ON conversations(user_id, updated_at DESC);

-- Note: user_id will be the Supabase auth user ID (UUID format)
-- For now, user_id can be NULL for existing conversations


