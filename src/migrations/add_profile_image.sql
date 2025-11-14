-- Migration: add profile image storage to user_profiles

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS profile_image TEXT;


