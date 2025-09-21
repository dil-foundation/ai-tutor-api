-- =============================================================================
-- PERMANENTLY DELETE STAGE 2 EXERCISE TABLES
-- =============================================================================
-- Warning: This script will permanently delete the tables and all their data.
-- This action cannot be undone.
-- =============================================================================

-- Drop the table for Stage 2, Exercise 1: Daily Routine Narration
DROP TABLE IF EXISTS public.ai_tutor_stage2_exercise1_daily_routine CASCADE;

-- Drop the table for Stage 2, Exercise 2: Question Answer Chat Practice
DROP TABLE IF EXISTS public.ai_tutor_stage2_exercise2_question_answer CASCADE;

-- Drop the table for Stage 2, Exercise 3: Roleplay Simulation
DROP TABLE IF EXISTS public.ai_tutor_stage2_exercise3_roleplay CASCADE;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- After running this script, the specified tables should no longer exist.
-- =============================================================================
