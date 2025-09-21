-- =============================================================================
-- PERMANENTLY DELETE STAGE 4 EXERCISE TABLES
-- =============================================================================
-- Warning: This script will permanently delete the tables and all their data.
-- This action cannot be undone.
-- =============================================================================

-- Drop the table for Stage 4, Exercise 1: Opinion Expression & Debate
DROP TABLE IF EXISTS public.ai_tutor_stage4_exercise1_opinion_debate CASCADE;

-- Drop the table for Stage 4, Exercise 2: Professional Interview Simulation
DROP TABLE IF EXISTS public.ai_tutor_stage4_exercise2_interview_simulation CASCADE;

-- Drop the table for Stage 4, Exercise 3: News Summarization & Analysis
DROP TABLE IF EXISTS public.ai_tutor_stage4_exercise3_news_summarization CASCADE;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- After running this script, the specified tables should no longer exist.
-- You can verify this by trying to select from them, which should result in an error.
-- =============================================================================
