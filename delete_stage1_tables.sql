-- =============================================================================
-- PERMANENTLY DELETE STAGE 1 EXERCISE TABLES
-- =============================================================================
-- Warning: This script will permanently delete the tables and all their data.
-- This action cannot be undone.
-- =============================================================================

-- Drop the table for Stage 1, Exercise 1: Repeat After Me Phrases
DROP TABLE IF EXISTS public.ai_tutor_stage1_exercise1_repeat_after_me CASCADE;

-- Drop the table for Stage 1, Exercise 2: Quick Response Prompts
DROP TABLE IF EXISTS public.ai_tutor_stage1_exercise2_quick_response CASCADE;

-- Drop the table for Stage 1, Exercise 3: Functional Dialogue
DROP TABLE IF EXISTS public.ai_tutor_stage1_exercise3_functional_dialogue CASCADE;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- After running this script, the specified tables should no longer exist.
-- =============================================================================
