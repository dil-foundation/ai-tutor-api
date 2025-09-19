-- =============================================================================
-- AI English Tutor - Hierarchical Structure Database Schema
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- MAIN HIERARCHICAL TABLE: STAGES, EXERCISES, AND TOPICS
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.ai_tutor_content_hierarchy (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4(),
    
    -- Hierarchy Level (stage, exercise, topic)
    level TEXT NOT NULL CHECK (level IN ('stage', 'exercise', 'topic')),
    
    -- Hierarchy Path (e.g., "1.2.3" for Stage 1, Exercise 2, Topic 3)
    hierarchy_path TEXT NOT NULL,
    
    -- Parent Reference (NULL for stages, stage_id for exercises, exercise_id for topics)
    parent_id INTEGER REFERENCES public.ai_tutor_content_hierarchy(id),
    
    -- Content Information
    title TEXT NOT NULL,
    title_urdu TEXT,
    description TEXT,
    description_urdu TEXT,
    
    -- Stage-specific fields (only for level='stage')
    stage_number INTEGER,
    difficulty_level TEXT CHECK (difficulty_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
    stage_order INTEGER,
    
    -- Exercise-specific fields (only for level='exercise')
    exercise_number INTEGER,
    exercise_type TEXT,
    exercise_order INTEGER,
    
    -- Topic-specific fields (only for level='topic')
    topic_number INTEGER,
    topic_data JSONB, -- Stores all topic-specific data (phrases, questions, scenarios, etc.)
    topic_order INTEGER,
    
    -- Common fields
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Primary hierarchy indexes
CREATE INDEX IF NOT EXISTS idx_content_hierarchy_level ON public.ai_tutor_content_hierarchy(level);
CREATE INDEX IF NOT EXISTS idx_content_hierarchy_path ON public.ai_tutor_content_hierarchy(hierarchy_path);
CREATE INDEX IF NOT EXISTS idx_content_hierarchy_parent ON public.ai_tutor_content_hierarchy(parent_id);

-- Stage-specific indexes
CREATE INDEX IF NOT EXISTS idx_content_hierarchy_stage_number ON public.ai_tutor_content_hierarchy(stage_number) WHERE level = 'stage';
CREATE INDEX IF NOT EXISTS idx_content_hierarchy_difficulty ON public.ai_tutor_content_hierarchy(difficulty_level) WHERE level = 'stage';

-- Exercise-specific indexes
CREATE INDEX IF NOT EXISTS idx_content_hierarchy_exercise_number ON public.ai_tutor_content_hierarchy(exercise_number) WHERE level = 'exercise';
CREATE INDEX IF NOT EXISTS idx_content_hierarchy_exercise_type ON public.ai_tutor_content_hierarchy(exercise_type) WHERE level = 'exercise';

-- Topic-specific indexes
CREATE INDEX IF NOT EXISTS idx_content_hierarchy_topic_number ON public.ai_tutor_content_hierarchy(topic_number) WHERE level = 'topic';

-- =============================================================================
-- INSERT STAGE DATA
-- =============================================================================

INSERT INTO public.ai_tutor_content_hierarchy (level, hierarchy_path, parent_id, title, title_urdu, description, description_urdu, stage_number, difficulty_level, stage_order) VALUES
('stage', '1', NULL, 'Foundation Speaking', 'بنیادی بول چال', 'Basic conversation skills and pronunciation practice for beginners', 'ابتدائی سطح کے لیے بنیادی گفتگو کی مہارتیں اور تلفظ کی مشق', 1, 'A1', 1),
('stage', '2', NULL, 'Daily Communication', 'روزمرہ کی بات چیت', 'Practical daily life conversations and routine expressions', 'عملی روزمرہ کی زندگی کی گفتگو اور معمول کے اظہارات', 2, 'A2', 2),
('stage', '3', NULL, 'Storytelling & Discussion', 'کہانی سنانا اور بحث', 'Narrative skills and group discussion practice', 'بیانیہ مہارتیں اور گروپ بحث کی مشق', 3, 'B1', 3),
('stage', '4', NULL, 'Professional Communication', 'پیشہ ورانہ مواصلات', 'Business and professional communication skills', 'کاروباری اور پیشہ ورانہ مواصلات کی مہارتیں', 4, 'B2', 4),
('stage', '5', NULL, 'Advanced Debate & Analysis', 'اعلیٰ بحث اور تجزیہ', 'Complex argumentation and academic presentation skills', 'پیچیدہ بحث اور تعلیمی پیشکش کی مہارتیں', 5, 'C1', 5),
('stage', '6', NULL, 'Mastery & Diplomacy', 'مہارت اور سفارت کاری', 'Spontaneous speaking and diplomatic communication mastery', 'خودکار بول چال اور سفارتی مواصلات میں مہارت', 6, 'C2', 6);

-- =============================================================================
-- INSERT EXERCISE DATA
-- =============================================================================

-- Stage 1 Exercises
INSERT INTO public.ai_tutor_content_hierarchy (level, hierarchy_path, parent_id, title, title_urdu, description, description_urdu, exercise_number, exercise_type, exercise_order) VALUES
('exercise', '1.1', 1, 'Repeat After Me Phrases', 'میرے بعد دہرائیں', 'Practice pronunciation with common English phrases', 'عام انگریزی جملوں کے ساتھ تلفظ کی مشق', 1, 'pronunciation', 1),
('exercise', '1.2', 1, 'Quick Response Prompts', 'فوری جواب کے اشارے', 'Develop quick thinking and response skills', 'تیز سوچ اور جواب کی مہارتیں تیار کریں', 2, 'response', 2),
('exercise', '1.3', 1, 'Functional Dialogue', 'عملی مکالمہ', 'Learn essential conversation patterns', 'ضروری گفتگو کے نمونے سیکھیں', 3, 'dialogue', 3);

-- Stage 2 Exercises
INSERT INTO public.ai_tutor_content_hierarchy (level, hierarchy_path, parent_id, title, title_urdu, description, description_urdu, exercise_number, exercise_type, exercise_order) VALUES
('exercise', '2.1', 2, 'Daily Routine Narration', 'روزمرہ کی روایت بیان', 'Describe daily activities and routines', 'روزمرہ کی سرگرمیوں اور معمولات کا بیان', 1, 'narration', 1),
('exercise', '2.2', 2, 'Question Answer Chat Practice', 'سوال جواب چاٹ کی مشق', 'Practice conversational question-answer patterns', 'گفتگو کے سوال جواب کے نمونوں کی مشق', 2, 'conversation', 2),
('exercise', '2.3', 2, 'Roleplay Simulation', 'کردار ادا کرنے کی مشق', 'Simulate real-life scenarios through roleplay', 'کردار ادا کرنے کے ذریعے حقیقی زندگی کے مناظر کی مشق', 3, 'roleplay', 3);

-- Stage 3 Exercises
INSERT INTO public.ai_tutor_content_hierarchy (level, hierarchy_path, parent_id, title, title_urdu, description, description_urdu, exercise_number, exercise_type, exercise_order) VALUES
('exercise', '3.1', 3, 'Storytelling Narration', 'کہانی سنانے کا بیان', 'Develop narrative skills and story structure', 'بیانیہ مہارتیں اور کہانی کی ساخت تیار کریں', 1, 'storytelling', 1),
('exercise', '3.2', 3, 'Group Discussion Simulation', 'گروپ بحث کی مشق', 'Practice group discussion and opinion sharing', 'گروپ بحث اور رائے کا اشتراک کرنے کی مشق', 2, 'discussion', 2),
('exercise', '3.3', 3, 'Problem Solving Conversations', 'مسئلہ حل کرنے کی گفتگو', 'Handle complex problem-solving discussions', 'پیچیدہ مسئلہ حل کرنے کی گفتگو کا انتظام', 3, 'problem_solving', 3);

-- Stage 4 Exercises
INSERT INTO public.ai_tutor_content_hierarchy (level, hierarchy_path, parent_id, title, title_urdu, description, description_urdu, exercise_number, exercise_type, exercise_order) VALUES
('exercise', '4.1', 4, 'Business Presentation Skills', 'کاروباری پیشکش کی مہارتیں', 'Professional presentation and public speaking', 'پیشہ ورانہ پیشکش اور عوامی تقریر', 1, 'presentation', 1),
('exercise', '4.2', 4, 'Negotiation & Persuasion', 'مذاکرات اور قائل کرنا', 'Advanced negotiation and persuasion techniques', 'اعلیٰ مذاکرات اور قائل کرنے کی تکنیک', 2, 'negotiation', 2),
('exercise', '4.3', 4, 'Leadership Communication', 'قیادت کی مواصلات', 'Leadership communication and team management', 'قیادت کی مواصلات اور ٹیم مینجمنٹ', 3, 'leadership', 3);

-- Stage 5 Exercises
INSERT INTO public.ai_tutor_content_hierarchy (level, hierarchy_path, parent_id, title, title_urdu, description, description_urdu, exercise_number, exercise_type, exercise_order) VALUES
('exercise', '5.1', 5, 'Advanced Debate & Argumentation', 'اعلیٰ بحث اور دلیل', 'Complex argumentation and critical thinking', 'پیچیدہ دلیل اور تنقیدی سوچ', 1, 'debate', 1),
('exercise', '5.2', 5, 'Academic Presentation & Analysis', 'تعلیمی پیشکش اور تجزیہ', 'Academic presentation and analytical skills', 'تعلیمی پیشکش اور تجزیاتی مہارتیں', 2, 'academic', 2),
('exercise', '5.3', 5, 'Professional Interview Mastery', 'پیشہ ورانہ انٹرویو میں مہارت', 'Advanced interview skills and professional communication', 'اعلیٰ انٹرویو کی مہارتیں اور پیشہ ورانہ مواصلات', 3, 'interview', 3);

-- Stage 6 Exercises
INSERT INTO public.ai_tutor_content_hierarchy (level, hierarchy_path, parent_id, title, title_urdu, description, description_urdu, exercise_number, exercise_type, exercise_order) VALUES
('exercise', '6.1', 6, 'Advanced Spontaneous Speaking', 'اعلیٰ خودکار بول چال', 'Spontaneous speaking and natural fluency', 'خودکار بول چال اور قدرتی روانی', 1, 'spontaneous', 1),
('exercise', '6.2', 6, 'Advanced Diplomatic Communication', 'اعلیٰ سفارتی مواصلات', 'Diplomatic communication and sensitive situations', 'سفارتی مواصلات اور حساس حالات', 2, 'diplomatic', 2),
('exercise', '6.3', 6, 'Advanced Academic Debate', 'اعلیٰ تعلیمی بحث', 'Advanced academic debate and formal argumentation', 'اعلیٰ تعلیمی بحث اور رسمی دلیل', 3, 'academic_debate', 3);

-- =============================================================================
-- INSERT SAMPLE TOPIC DATA (Stage 1, Exercise 1 - Repeat After Me Phrases)
-- =============================================================================

INSERT INTO public.ai_tutor_content_hierarchy (level, hierarchy_path, parent_id, title, title_urdu, description, description_urdu, topic_number, topic_data, topic_order) VALUES
('topic', '1.1.1', 7, 'Hello, how are you?', 'ہیلو، آپ کیسے ہیں؟', 'Basic greeting phrase', 'بنیادی سلام کا جملہ', 1, '{"phrase": "Hello, how are you?", "urdu_meaning": "ہیلو، آپ کیسے ہیں؟", "category": "greetings", "difficulty": "beginner"}', 1),
('topic', '1.1.2', 7, 'My name is Ali.', 'میرا نام علی ہے۔', 'Self-introduction phrase', 'خود تعارف کا جملہ', 2, '{"phrase": "My name is Ali.", "urdu_meaning": "میرا نام علی ہے۔", "category": "introduction", "difficulty": "beginner"}', 2),
('topic', '1.1.3', 7, 'I am fine, thank you.', 'میں ٹھیک ہوں، شکریہ۔', 'Response to how are you', 'آپ کیسے ہیں کے جواب میں', 3, '{"phrase": "I am fine, thank you.", "urdu_meaning": "میں ٹھیک ہوں، شکریہ۔", "category": "greetings", "difficulty": "beginner"}', 3),
('topic', '1.1.4', 7, 'Nice to meet you.', 'آپ سے مل کر خوشی ہوئی۔', 'Meeting someone new', 'نئے شخص سے ملاقات', 4, '{"phrase": "Nice to meet you.", "urdu_meaning": "آپ سے مل کر خوشی ہوئی۔", "category": "greetings", "difficulty": "beginner"}', 4),
('topic', '1.1.5', 7, 'What is your name?', 'آپ کا نام کیا ہے؟', 'Asking for name', 'نام پوچھنا', 5, '{"phrase": "What is your name?", "urdu_meaning": "آپ کا نام کیا ہے؟", "category": "introduction", "difficulty": "beginner"}', 5);

-- =============================================================================
-- HELPER FUNCTIONS FOR HIERARCHY NAVIGATION
-- =============================================================================

-- Function to get all stages
CREATE OR REPLACE FUNCTION get_all_stages()
RETURNS TABLE (
    stage_id INTEGER,
    stage_number INTEGER,
    title TEXT,
    title_urdu TEXT,
    description TEXT,
    difficulty_level TEXT,
    stage_order INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        h.id,
        h.stage_number,
        h.title,
        h.title_urdu,
        h.description,
        h.difficulty_level,
        h.stage_order
    FROM public.ai_tutor_content_hierarchy h
    WHERE h.level = 'stage'
    ORDER BY h.stage_order;
END;
$$ LANGUAGE plpgsql;

-- Function to get exercises for a specific stage
CREATE OR REPLACE FUNCTION get_exercises_for_stage(stage_num INTEGER)
RETURNS TABLE (
    exercise_id INTEGER,
    exercise_number INTEGER,
    title TEXT,
    title_urdu TEXT,
    description TEXT,
    exercise_type TEXT,
    exercise_order INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        h.id,
        h.exercise_number,
        h.title,
        h.title_urdu,
        h.description,
        h.exercise_type,
        h.exercise_order
    FROM public.ai_tutor_content_hierarchy h
    WHERE h.level = 'exercise' 
    AND h.parent_id = (
        SELECT id FROM public.ai_tutor_content_hierarchy 
        WHERE level = 'stage' AND stage_number = stage_num
    )
    ORDER BY h.exercise_order;
END;
$$ LANGUAGE plpgsql;

-- Function to get topics for a specific exercise
CREATE OR REPLACE FUNCTION get_topics_for_exercise(stage_num INTEGER, exercise_num INTEGER)
RETURNS TABLE (
    topic_id INTEGER,
    topic_number INTEGER,
    title TEXT,
    title_urdu TEXT,
    description TEXT,
    topic_data JSONB,
    topic_order INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        h.id,
        h.topic_number,
        h.title,
        h.title_urdu,
        h.description,
        h.topic_data,
        h.topic_order
    FROM public.ai_tutor_content_hierarchy h
    WHERE h.level = 'topic' 
    AND h.parent_id = (
        SELECT id FROM public.ai_tutor_content_hierarchy 
        WHERE level = 'exercise' 
        AND parent_id = (
            SELECT id FROM public.ai_tutor_content_hierarchy 
            WHERE level = 'stage' AND stage_number = stage_num
        )
        AND exercise_number = exercise_num
    )
    ORDER BY h.topic_order;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

ALTER TABLE public.ai_tutor_content_hierarchy ENABLE ROW LEVEL SECURITY;

-- Policy for public read access
CREATE POLICY "Anyone can view content hierarchy" ON public.ai_tutor_content_hierarchy FOR SELECT USING (true);

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

GRANT ALL ON public.ai_tutor_content_hierarchy TO anon, authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Verify the hierarchical structure
SELECT 'HIERARCHICAL STRUCTURE OVERVIEW:' as info;

-- Show all stages
SELECT 'STAGES:' as level, stage_number, title, title_urdu, difficulty_level 
FROM public.ai_tutor_content_hierarchy 
WHERE level = 'stage' 
ORDER BY stage_order;

-- Show exercises for Stage 1
SELECT 'STAGE 1 EXERCISES:' as level, exercise_number, title, title_urdu, exercise_type 
FROM public.ai_tutor_content_hierarchy 
WHERE level = 'exercise' AND parent_id = 1 
ORDER BY exercise_order;

-- Show topics for Stage 1, Exercise 1
SELECT 'STAGE 1 EXERCISE 1 TOPICS:' as level, topic_number, title, title_urdu, topic_data 
FROM public.ai_tutor_content_hierarchy 
WHERE level = 'topic' AND parent_id = 7 
ORDER BY topic_order;

-- Test helper functions
SELECT 'Testing get_all_stages():' as test;
SELECT * FROM get_all_stages();

SELECT 'Testing get_exercises_for_stage(1):' as test;
SELECT * FROM get_exercises_for_stage(1);

SELECT 'Testing get_topics_for_exercise(1, 1):' as test;
SELECT * FROM get_topics_for_exercise(1, 1);
