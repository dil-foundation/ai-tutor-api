-- =============================================================================
-- PERMANENTLY DELETE STAGE 3 EXERCISE TABLES
-- =============================================================================
-- Warning: This script will permanently delete the tables and all their data.
-- This action cannot be undone.
-- =============================================================================

-- Drop the table for Stage 3, Exercise 1: Storytelling Narration
DROP TABLE IF EXISTS public.ai_tutor_stage3_exercise1_storytelling CASCADE;

-- Drop the table for Stage 3, Exercise 2: Group Discussion Simulation
DROP TABLE IF EXISTS public.ai_tutor_stage3_exercise2_group_discussion CASCADE;

-- Drop the table for Stage 3, Exercise 3: Problem Solving Conversations
DROP TABLE IF EXISTS public.ai_tutor_stage3_exercise3_problem_solving CASCADE;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- After running this script, the specified tables should no longer exist.
-- =============================================================================
