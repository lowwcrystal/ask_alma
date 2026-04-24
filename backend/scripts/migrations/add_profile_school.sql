-- Migration: add school selection to user profiles

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS school TEXT;


