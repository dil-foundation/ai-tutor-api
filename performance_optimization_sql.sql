-- Performance Optimization SQL for AI Tutor Dashboard
-- Execute these queries in your Supabase SQL editor

-- 1. Create optimized view for student progress overview
CREATE OR REPLACE VIEW teacher_dashboard_student_overview AS
SELECT 
    ups.user_id,
    ups.current_stage,
    ups.current_exercise,
    ups.overall_progress_percentage,
    ups.last_activity_date,
    ups.total_time_spent_minutes,
    ups.total_exercises_completed,
    ups.streak_days,
    ups.longest_streak,
    ups.updated_at,
    
    -- Student profile data
    p.first_name,
    p.last_name,
    p.email,
    p.role,
    
    -- Aggregated exercise progress
    COALESCE(AVG(uep.average_score), 0) as avg_score,
    COALESCE(MAX(uep.best_score), 0) as best_score,
    COALESCE(SUM(uep.total_score), 0) as total_score,
    COUNT(uep.exercise_id) as exercises_attempted,
    
    -- Stage information
    s.title as stage_title,
    s.description as stage_description,
    
    -- Risk assessment
    CASE 
        WHEN ups.overall_progress_percentage < 50 OR COALESCE(AVG(uep.average_score), 0) < 60 THEN true
        ELSE false
    END as is_at_risk,
    
    -- Activity status
    CASE 
        WHEN ups.last_activity_date >= CURRENT_DATE - INTERVAL '7 days' THEN 'active'
        WHEN ups.last_activity_date >= CURRENT_DATE - INTERVAL '30 days' THEN 'inactive'
        ELSE 'very_inactive'
    END as activity_status

FROM ai_tutor_user_progress_summary ups
LEFT JOIN profiles p ON ups.user_id = p.id
LEFT JOIN ai_tutor_user_exercise_progress uep ON ups.user_id = uep.user_id 
LEFT JOIN ai_tutor_content_hierarchy_stages s ON ups.current_stage = s.stage_number
WHERE p.role = 'student'  -- Only include students
GROUP BY 
    ups.user_id, ups.current_stage, ups.current_exercise, 
    ups.overall_progress_percentage, ups.last_activity_date,
    ups.total_time_spent_minutes, ups.total_exercises_completed,
    ups.streak_days, ups.longest_streak, ups.updated_at,
    p.first_name, p.last_name, p.email, p.role,
    s.title, s.description;

-- 2. Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_user_progress_summary_stage 
ON ai_tutor_user_progress_summary(current_stage);

CREATE INDEX IF NOT EXISTS idx_user_progress_summary_updated 
ON ai_tutor_user_progress_summary(updated_at);

CREATE INDEX IF NOT EXISTS idx_user_progress_summary_user_stage 
ON ai_tutor_user_progress_summary(user_id, current_stage);

CREATE INDEX IF NOT EXISTS idx_user_exercise_progress_user_stage 
ON ai_tutor_user_exercise_progress(user_id, stage_id);

CREATE INDEX IF NOT EXISTS idx_profiles_role 
ON profiles(role);

-- 3. Create function for fast progress overview
CREATE OR REPLACE FUNCTION get_teacher_dashboard_overview_fast(
    p_search_query TEXT DEFAULT NULL,
    p_stage_id INTEGER DEFAULT NULL,
    p_time_range TEXT DEFAULT 'all_time'
)
RETURNS TABLE (
    user_id UUID,
    student_name TEXT,
    email TEXT,
    current_stage INTEGER,
    stage_title TEXT,
    current_lesson TEXT,
    avg_score NUMERIC,
    best_score NUMERIC,
    progress_percentage NUMERIC,
    last_activity_date DATE,
    total_time_minutes INTEGER,
    exercises_completed INTEGER,
    exercises_attempted BIGINT,
    is_at_risk BOOLEAN,
    activity_status TEXT,
    ai_feedback_text TEXT,
    ai_feedback_sentiment TEXT
) 
LANGUAGE plpgsql
AS $$
DECLARE
    start_date DATE;
    end_date DATE;
BEGIN
    -- Calculate date range
    CASE p_time_range
        WHEN 'today' THEN
            start_date := CURRENT_DATE;
            end_date := CURRENT_DATE;
        WHEN 'this_week' THEN
            start_date := CURRENT_DATE - EXTRACT(DOW FROM CURRENT_DATE)::INTEGER;
            end_date := CURRENT_DATE;
        WHEN 'this_month' THEN
            start_date := DATE_TRUNC('month', CURRENT_DATE)::DATE;
            end_date := CURRENT_DATE;
        WHEN 'this_year' THEN
            start_date := DATE_TRUNC('year', CURRENT_DATE)::DATE;
            end_date := CURRENT_DATE;
        ELSE
            start_date := NULL;
            end_date := NULL;
    END CASE;

    RETURN QUERY
    SELECT 
        sov.user_id,
        CASE 
            WHEN sov.first_name IS NOT NULL AND sov.last_name IS NOT NULL 
            THEN CONCAT(sov.first_name, ' ', sov.last_name)
            WHEN sov.first_name IS NOT NULL 
            THEN sov.first_name
            WHEN sov.last_name IS NOT NULL 
            THEN sov.last_name
            ELSE sov.email
        END as student_name,
        sov.email,
        sov.current_stage,
        sov.stage_title,
        sov.stage_description as current_lesson,
        ROUND(sov.avg_score, 1) as avg_score,
        ROUND(sov.best_score, 1) as best_score,
        ROUND(sov.overall_progress_percentage, 1) as progress_percentage,
        sov.last_activity_date,
        sov.total_time_spent_minutes,
        sov.total_exercises_completed,
        sov.exercises_attempted,
        sov.is_at_risk,
        sov.activity_status,
        -- Generate AI feedback based on performance
        CASE 
            WHEN sov.overall_progress_percentage >= 80 AND sov.avg_score >= 85 THEN
                'Exceptional performance across all areas. Ready for advanced challenges.'
            WHEN sov.overall_progress_percentage >= 60 AND sov.avg_score >= 70 THEN
                'Making steady progress with good understanding. Continue practicing.'
            WHEN sov.overall_progress_percentage >= 40 AND sov.avg_score >= 60 THEN
                'Making progress but needs additional support and practice.'
            ELSE
                'Requires immediate attention and personalized support.'
        END as ai_feedback_text,
        CASE 
            WHEN sov.overall_progress_percentage >= 80 AND sov.avg_score >= 85 THEN 'positive'
            WHEN sov.overall_progress_percentage >= 60 AND sov.avg_score >= 70 THEN 'positive'
            WHEN sov.overall_progress_percentage >= 40 AND sov.avg_score >= 60 THEN 'mixed'
            ELSE 'needs_attention'
        END as ai_feedback_sentiment
        
    FROM teacher_dashboard_student_overview sov
    WHERE 
        (p_stage_id IS NULL OR sov.current_stage = p_stage_id)
        AND (start_date IS NULL OR sov.updated_at >= start_date)
        AND (end_date IS NULL OR sov.updated_at <= end_date)
        AND (p_search_query IS NULL OR 
             LOWER(CONCAT(sov.first_name, ' ', sov.last_name)) LIKE LOWER('%' || p_search_query || '%') OR
             LOWER(sov.email) LIKE LOWER('%' || p_search_query || '%'))
    ORDER BY sov.overall_progress_percentage DESC, sov.last_activity_date DESC;
END;
$$;

-- 4. Create function for progress metrics
CREATE OR REPLACE FUNCTION get_progress_metrics_fast(
    p_stage_id INTEGER DEFAULT NULL,
    p_time_range TEXT DEFAULT 'all_time'
)
RETURNS TABLE (
    total_students BIGINT,
    avg_completion_percentage NUMERIC,
    avg_score NUMERIC,
    students_at_risk_count BIGINT,
    active_students_count BIGINT,
    inactive_students_count BIGINT
) 
LANGUAGE plpgsql
AS $$
DECLARE
    start_date DATE;
    end_date DATE;
BEGIN
    -- Calculate date range (same logic as above)
    CASE p_time_range
        WHEN 'today' THEN
            start_date := CURRENT_DATE;
            end_date := CURRENT_DATE;
        WHEN 'this_week' THEN
            start_date := CURRENT_DATE - EXTRACT(DOW FROM CURRENT_DATE)::INTEGER;
            end_date := CURRENT_DATE;
        WHEN 'this_month' THEN
            start_date := DATE_TRUNC('month', CURRENT_DATE)::DATE;
            end_date := CURRENT_DATE;
        WHEN 'this_year' THEN
            start_date := DATE_TRUNC('year', CURRENT_DATE)::DATE;
            end_date := CURRENT_DATE;
        ELSE
            start_date := NULL;
            end_date := NULL;
    END CASE;

    RETURN QUERY
    SELECT 
        COUNT(*) as total_students,
        ROUND(AVG(sov.overall_progress_percentage), 1) as avg_completion_percentage,
        ROUND(AVG(sov.avg_score), 1) as avg_score,
        COUNT(*) FILTER (WHERE sov.is_at_risk = true) as students_at_risk_count,
        COUNT(*) FILTER (WHERE sov.activity_status = 'active') as active_students_count,
        COUNT(*) FILTER (WHERE sov.activity_status IN ('inactive', 'very_inactive')) as inactive_students_count
    FROM teacher_dashboard_student_overview sov
    WHERE 
        (p_stage_id IS NULL OR sov.current_stage = p_stage_id)
        AND (start_date IS NULL OR sov.updated_at >= start_date)
        AND (end_date IS NULL OR sov.updated_at <= end_date);
END;
$$;

-- 5. Grant permissions (adjust as needed for your setup)
GRANT SELECT ON teacher_dashboard_student_overview TO authenticated;
GRANT EXECUTE ON FUNCTION get_teacher_dashboard_overview_fast TO authenticated;
GRANT EXECUTE ON FUNCTION get_progress_metrics_fast TO authenticated;

-- 6. Create materialized view for even better performance (optional)
-- Refresh this view periodically (e.g., every 15 minutes)
CREATE MATERIALIZED VIEW IF NOT EXISTS teacher_dashboard_cache AS
SELECT * FROM teacher_dashboard_student_overview;

CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_dashboard_cache_user_id 
ON teacher_dashboard_cache(user_id);

-- Function to refresh the materialized view
CREATE OR REPLACE FUNCTION refresh_teacher_dashboard_cache()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY teacher_dashboard_cache;
END;
$$;

-- 7. Performance monitoring queries
-- Use these to monitor query performance

-- Check slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
WHERE query LIKE '%teacher_dashboard%' 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE tablename IN (
    'ai_tutor_user_progress_summary',
    'ai_tutor_user_exercise_progress',
    'profiles'
)
ORDER BY idx_scan DESC;
