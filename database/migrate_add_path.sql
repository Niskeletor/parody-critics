-- Migration: Add path column to media table
-- This migration adds the path column if it doesn't exist

-- Add path column to media table
ALTER TABLE media ADD COLUMN path TEXT;

-- Update the table to reflect the changes
UPDATE media SET path = NULL WHERE path IS NULL;