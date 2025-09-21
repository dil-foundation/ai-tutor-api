-- =============================================================================
-- PERMANENTLY DELETE STAGE 6 EXERCISE TABLES
-- =============================================================================
-- Warning: This script will permanently delete the tables and all their data.
-- This action cannot be undone.
-- =============================================================================

-- Drop the table for Stage 6, Exercise 1: Advanced Spontaneous Speaking
DROP TABLE IF EXISTS public.ai_tutor_stage6_exercise1_spontaneous_speaking CASCADE;

-- Drop the table for Stage 6, Exercise 2: Advanced Diplomatic Communication
DROP TABLE IF EXISTS public.ai_tutor_stage6_exercise2_diplomatic_communication CASCADE;

-- Drop the table for Stage 6, Exercise 3: Advanced Academic Debate
DROP TABLE IF EXISTS public.ai_tutor_stage6_exercise3_academic_debate CASCADE;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- After running this script, the specified tables should no longer exist.
-- =============================================================================
