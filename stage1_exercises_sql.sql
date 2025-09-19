-- =============================================================================
-- AI English Tutor - Stage 1 Exercises Database Schema
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- STAGE 1 EXERCISE 1: REPEAT AFTER ME PHRASES
-- =============================================================================

-- Table for Repeat After Me Phrases
CREATE TABLE IF NOT EXISTS public.ai_tutor_stage1_exercise1_repeat_after_me (
    id SERIAL PRIMARY KEY,
    phrase TEXT NOT NULL,
    urdu_meaning TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert data for Repeat After Me Phrases
INSERT INTO public.ai_tutor_stage1_exercise1_repeat_after_me (phrase, urdu_meaning) VALUES
('Hello, how are you?', 'ہیلو، آپ کیسے ہیں؟'),
('My name is Ali.', 'میرا نام علی ہے۔'),
('I am fine, thank you.', 'میں ٹھیک ہوں، شکریہ۔'),
('Nice to meet you.', 'آپ سے مل کر خوشی ہوئی۔'),
('What is your name?', 'آپ کا نام کیا ہے؟'),
('I live in Karachi.', 'میں کراچی میں رہتا ہوں۔'),
('Where are you from?', 'آپ کہاں سے ہیں؟'),
('I am from Pakistan.', 'میں پاکستان سے ہوں۔'),
('I am learning English.', 'میں انگلش سیکھ رہا ہوں۔'),
('Can you help me?', 'کیا آپ میری مدد کر سکتے ہیں؟'),
('Yes, of course.', 'جی ہاں، بالکل۔'),
('I don''t understand.', 'مجھے سمجھ نہیں آیا۔'),
('Please speak slowly.', 'براہِ کرم آہستہ بولیں۔'),
('How do you say this in English?', 'یہ انگلش میں کیسے کہیں گے؟'),
('Good morning.', 'صبح بخیر۔'),
('Good afternoon.', 'دوپہر بخیر۔'),
('Good evening.', 'شام بخیر۔'),
('Good night.', 'شب بخیر۔'),
('See you later.', 'پھر ملیں گے۔'),
('Thank you very much.', 'آپ کا بہت شکریہ۔'),
('You''re welcome.', 'خوش آمدید۔'),
('What time is it?', 'کتنے بجے ہیں؟'),
('It is five o''clock.', 'پانچ بجے ہیں۔'),
('I have a question.', 'مجھے ایک سوال پوچھنا ہے۔'),
('Excuse me.', 'معاف کیجیے۔'),
('I am sorry.', 'مجھے افسوس ہے۔'),
('No problem.', 'کوئی مسئلہ نہیں۔'),
('I like to read books.', 'مجھے کتابیں پڑھنا پسند ہے۔'),
('I like playing cricket.', 'مجھے کرکٹ کھیلنا پسند ہے۔'),
('What do you do?', 'آپ کیا کرتے ہیں؟'),
('I am a student.', 'میں طالب علم ہوں۔'),
('I work in an office.', 'میں ایک دفتر میں کام کرتا ہوں۔'),
('How old are you?', 'آپ کی عمر کتنی ہے؟'),
('I am twenty years old.', 'میری عمر بیس سال ہے۔'),
('Do you speak English?', 'کیا آپ انگلش بولتے ہیں؟'),
('Yes, I speak English.', 'جی ہاں، میں انگلش بولتا ہوں۔'),
('No, I don''t speak English.', 'نہیں، میں انگلش نہیں بولتا۔'),
('I want to learn English.', 'میں انگلش سیکھنا چاہتا ہوں۔'),
('This is my first time.', 'یہ میری پہلی بار ہے۔'),
('I am very happy.', 'میں بہت خوش ہوں۔'),
('I am tired.', 'میں تھکا ہوا ہوں۔'),
('I am hungry.', 'میں بھوکا ہوں۔'),
('I am thirsty.', 'مجھے پیاس لگی ہے۔'),
('The weather is nice.', 'موسم خوشگوار ہے۔'),
('It is raining today.', 'آج بارش ہو رہی ہے۔'),
('I love my family.', 'مجھے اپنے خاندان سے محبت ہے۔'),
('I have two brothers.', 'میرے دو بھائی ہیں۔'),
('I have one sister.', 'میری ایک بہن ہے۔'),
('My favorite color is blue.', 'میرا پسندیدہ رنگ نیلا ہے۔'),
('I like to watch movies.', 'مجھے فلمیں دیکھنا پسند ہے۔');

-- =============================================================================
-- STAGE 1 EXERCISE 2: QUICK RESPONSE PROMPTS
-- =============================================================================

-- Table for Quick Response Prompts
CREATE TABLE IF NOT EXISTS public.ai_tutor_stage1_exercise2_quick_response (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    question_urdu TEXT NOT NULL,
    expected_answers TEXT[] NOT NULL,
    expected_answers_urdu TEXT[] NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'beginner',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert data for Quick Response Prompts
INSERT INTO public.ai_tutor_stage1_exercise2_quick_response (question, question_urdu, expected_answers, expected_answers_urdu, category, difficulty) VALUES
('Hi!', 'ہیلو!', ARRAY['Hello!', 'Hi!', 'Hey!', 'Good morning!', 'Good afternoon!'], ARRAY['ہیلو!', 'ہائے!', 'ہائے!', 'صبح بخیر!', 'دوپہر بخیر!'], 'greetings', 'beginner'),
('How are you?', 'آپ کیسے ہیں؟', ARRAY['I''m fine.', 'I''m good.', 'I''m well.', 'Fine, thank you.', 'Good, thanks.'], ARRAY['میں ٹھیک ہوں۔', 'میں اچھا ہوں۔', 'میں ٹھیک ہوں۔', 'ٹھیک، شکریہ۔', 'اچھا، شکریہ۔'], 'greetings', 'beginner'),
('What''s your name?', 'آپ کا نام کیا ہے؟', ARRAY['My name is Ali.', 'I''m Ali.', 'Ali.', 'My name''s Ali.'], ARRAY['میرا نام علی ہے۔', 'میں علی ہوں۔', 'علی۔', 'میرا نام علی ہے۔'], 'introduction', 'beginner'),
('Where are you from?', 'آپ کہاں سے ہیں؟', ARRAY['I''m from Pakistan.', 'Pakistan.', 'I come from Pakistan.', 'I''m Pakistani.'], ARRAY['میں پاکستان سے ہوں۔', 'پاکستان۔', 'میں پاکستان سے آیا ہوں۔', 'میں پاکستانی ہوں۔'], 'introduction', 'beginner'),
('Do you speak English?', 'کیا آپ انگریزی بولتے ہیں؟', ARRAY['Yes, I do.', 'Yes, I speak English.', 'A little.', 'I''m learning.'], ARRAY['ہاں، میں بولتا ہوں۔', 'ہاں، میں انگریزی بولتا ہوں۔', 'تھوڑی۔', 'میں سیکھ رہا ہوں۔'], 'language', 'beginner'),
('What do you do?', 'آپ کیا کرتے ہیں؟', ARRAY['I''m a student.', 'I study.', 'I work.', 'I''m working.'], ARRAY['میں طالب علم ہوں۔', 'میں پڑھتا ہوں۔', 'میں کام کرتا ہوں۔', 'میں کام کر رہا ہوں۔'], 'occupation', 'beginner'),
('How old are you?', 'آپ کی عمر کیا ہے؟', ARRAY['I''m twenty.', 'Twenty.', 'I''m 20.', 'Twenty years old.'], ARRAY['میں بیس سال کا ہوں۔', 'بیس۔', 'میں 20 کا ہوں۔', 'بیس سال کا۔'], 'personal', 'beginner'),
('What time is it?', 'کتنا بجے ہیں؟', ARRAY['I don''t know.', 'I''m not sure.', 'Let me check.', 'I don''t have a watch.'], ARRAY['میں نہیں جانتا۔', 'میں یقین سے نہیں کہہ سکتا۔', 'مجھے دیکھنے دو۔', 'میرے پاس گھڑی نہیں ہے۔'], 'time', 'beginner'),
('Are you hungry?', 'کیا آپ بھوکے ہیں؟', ARRAY['Yes, I am.', 'No, I''m not.', 'A little.', 'Very hungry.'], ARRAY['ہاں، میں ہوں۔', 'نہیں، میں نہیں۔', 'تھوڑی۔', 'بہت بھوک۔'], 'daily_life', 'beginner'),
('Do you like music?', 'کیا آپ کو موسیقی پسند ہے؟', ARRAY['Yes, I do.', 'No, I don''t.', 'I love music.', 'It''s okay.'], ARRAY['ہاں، مجھے پسند ہے۔', 'نہیں، مجھے پسند نہیں۔', 'مجھے موسیقی بہت پسند ہے۔', 'ٹھیک ہے۔'], 'preferences', 'beginner'),
('What''s your favorite color?', 'آپ کا پسندیدہ رنگ کیا ہے؟', ARRAY['Blue.', 'I like blue.', 'My favorite is blue.', 'Blue is my favorite.'], ARRAY['نیلا۔', 'مجھے نیلا پسند ہے۔', 'میرا پسندیدہ نیلا ہے۔', 'نیلا میرا پسندیدہ ہے۔'], 'preferences', 'beginner'),
('Can you help me?', 'کیا آپ میری مدد کر سکتے ہیں؟', ARRAY['Yes, of course.', 'Sure.', 'I''ll try.', 'What do you need?'], ARRAY['ہاں، بالکل۔', 'یقیناً۔', 'میں کوشش کروں گا۔', 'آپ کو کیا چاہیے؟'], 'help', 'beginner'),
('Do you understand?', 'کیا آپ سمجھتے ہیں؟', ARRAY['Yes, I do.', 'No, I don''t.', 'A little.', 'Not completely.'], ARRAY['ہاں، میں سمجھتا ہوں۔', 'نہیں، میں نہیں سمجھتا۔', 'تھوڑا۔', 'مکمل طور پر نہیں۔'], 'communication', 'beginner'),
('Is it raining?', 'کیا بارش ہو رہی ہے؟', ARRAY['Yes, it is.', 'No, it''s not.', 'I don''t know.', 'Let me check.'], ARRAY['ہاں، ہو رہی ہے۔', 'نہیں، نہیں ہو رہی۔', 'میں نہیں جانتا۔', 'مجھے دیکھنے دو۔'], 'weather', 'beginner'),
('Do you have brothers?', 'کیا آپ کے بھائی ہیں؟', ARRAY['Yes, I do.', 'No, I don''t.', 'I have one brother.', 'Two brothers.'], ARRAY['ہاں، میرے ہیں۔', 'نہیں، میرے نہیں۔', 'میرا ایک بھائی ہے۔', 'دو بھائی۔'], 'family', 'beginner'),
('What do you like to eat?', 'آپ کیا کھانا پسند کرتے ہیں؟', ARRAY['Rice.', 'I like rice.', 'Biryani.', 'I love biryani.'], ARRAY['چاول۔', 'مجھے چاول پسند ہیں۔', 'بریانی۔', 'مجھے بریانی بہت پسند ہے۔'], 'food', 'beginner'),
('Are you tired?', 'کیا آپ تھکے ہوئے ہیں؟', ARRAY['Yes, I am.', 'No, I''m not.', 'A little.', 'Very tired.'], ARRAY['ہاں، میں ہوں۔', 'نہیں، میں نہیں۔', 'تھوڑا۔', 'بہت تھکا۔'], 'daily_life', 'beginner'),
('Do you play sports?', 'کیا آپ کھیل کھیلتے ہیں؟', ARRAY['Yes, I do.', 'No, I don''t.', 'Cricket.', 'I play cricket.'], ARRAY['ہاں، میں کھیلتا ہوں۔', 'نہیں، میں نہیں کھیلتا۔', 'کرکٹ۔', 'میں کرکٹ کھیلتا ہوں۔'], 'activities', 'beginner'),
('What''s the weather like?', 'موسم کیسا ہے؟', ARRAY['It''s nice.', 'It''s hot.', 'It''s cold.', 'It''s raining.'], ARRAY['اچھا ہے۔', 'گرم ہے۔', 'ٹھنڈا ہے۔', 'بارش ہو رہی ہے۔'], 'weather', 'beginner'),
('Do you watch movies?', 'کیا آپ فلمیں دیکھتے ہیں؟', ARRAY['Yes, I do.', 'No, I don''t.', 'Sometimes.', 'I love movies.'], ARRAY['ہاں، میں دیکھتا ہوں۔', 'نہیں، میں نہیں دیکھتا۔', 'کبھی کبھی۔', 'مجھے فلمیں بہت پسند ہیں۔'], 'entertainment', 'beginner'),
('What''s your phone number?', 'آپ کا فون نمبر کیا ہے؟', ARRAY['I don''t know.', 'I''m not sure.', 'Let me check.', 'I don''t remember.'], ARRAY['میں نہیں جانتا۔', 'میں یقین سے نہیں کہہ سکتا۔', 'مجھے دیکھنے دو۔', 'مجھے یاد نہیں۔'], 'personal', 'beginner'),
('Do you drive?', 'کیا آپ گاڑی چلاتے ہیں؟', ARRAY['Yes, I do.', 'No, I don''t.', 'I''m learning.', 'Not yet.'], ARRAY['ہاں، میں چلاتا ہوں۔', 'نہیں، میں نہیں چلاتا۔', 'میں سیکھ رہا ہوں۔', 'ابھی نہیں۔'], 'transportation', 'beginner'),
('What''s your favorite subject?', 'آپ کا پسندیدہ مضمون کیا ہے؟', ARRAY['English.', 'Math.', 'Science.', 'I like English.'], ARRAY['انگریزی۔', 'ریاضی۔', 'سائنس۔', 'مجھے انگریزی پسند ہے۔'], 'education', 'beginner'),
('Do you have pets?', 'کیا آپ کے پاس پالتو جانور ہیں؟', ARRAY['Yes, I do.', 'No, I don''t.', 'A dog.', 'I have a cat.'], ARRAY['ہاں، میرے پاس ہیں۔', 'نہیں، میرے پاس نہیں۔', 'ایک کتا۔', 'میرے پاس ایک بلی ہے۔'], 'personal', 'beginner'),
('What do you want to do?', 'آپ کیا کرنا چاہتے ہیں؟', ARRAY['I want to learn.', 'I want to study.', 'I want to work.', 'I want to travel.'], ARRAY['میں سیکھنا چاہتا ہوں۔', 'میں پڑھنا چاہتا ہوں۔', 'میں کام کرنا چاہتا ہوں۔', 'میں سفر کرنا چاہتا ہوں۔'], 'goals', 'beginner');

-- =============================================================================
-- STAGE 1 EXERCISE 3: FUNCTIONAL DIALOGUE
-- =============================================================================

-- Table for Functional Dialogue
CREATE TABLE IF NOT EXISTS public.ai_tutor_stage1_exercise3_functional_dialogue (
    id SERIAL PRIMARY KEY,
    ai_prompt TEXT NOT NULL,
    ai_prompt_urdu TEXT NOT NULL,
    expected_keywords TEXT[] NOT NULL,
    expected_keywords_urdu TEXT[] NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'beginner',
    context TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert data for Functional Dialogue
INSERT INTO public.ai_tutor_stage1_exercise3_functional_dialogue (ai_prompt, ai_prompt_urdu, expected_keywords, expected_keywords_urdu, category, difficulty, context) VALUES
('Hi! My name is Sarah. What is your name?', 'ہیلو! میرا نام سارہ ہے۔ آپ کا نام کیا ہے؟', ARRAY['name', 'my', 'is', 'what'], ARRAY['نام', 'میرا', 'ہے', 'کیا'], 'introduction', 'beginner', 'First meeting scenario'),
('Nice to meet you! Where are you from?', 'آپ سے مل کر خوشی ہوئی! آپ کہاں سے ہیں؟', ARRAY['from', 'where', 'country', 'city'], ARRAY['سے', 'کہاں', 'ملک', 'شہر'], 'introduction', 'beginner', 'Getting to know someone'),
('How are you today? Are you feeling good?', 'آج آپ کیسے ہیں؟ کیا آپ اچھا محسوس کر رہے ہیں؟', ARRAY['fine', 'good', 'well', 'feeling', 'today'], ARRAY['ٹھیک', 'اچھا', 'محسوس', 'آج'], 'greetings', 'beginner', 'Daily conversation'),
('Do you speak English? How long have you been learning?', 'کیا آپ انگریزی بولتے ہیں؟ آپ کتنی دیر سے سیکھ رہے ہیں؟', ARRAY['speak', 'English', 'learning', 'long', 'time'], ARRAY['بولتے', 'انگریزی', 'سیکھ', 'دیر', 'وقت'], 'language', 'beginner', 'Language learning discussion'),
('What do you do? Are you a student or do you work?', 'آپ کیا کرتے ہیں؟ کیا آپ طالب علم ہیں یا کام کرتے ہیں؟', ARRAY['student', 'work', 'job', 'study', 'do'], ARRAY['طالب علم', 'کام', 'نوکری', 'پڑھائی', 'کرتے'], 'occupation', 'beginner', 'Professional background'),
('How old are you? You look young!', 'آپ کی عمر کیا ہے؟ آپ جوان لگتے ہیں!', ARRAY['old', 'age', 'years', 'young', 'twenty'], ARRAY['عمر', 'سال', 'جوان', 'بیس'], 'personal', 'beginner', 'Age discussion'),
('What time is it now? Do you have a watch?', 'اب کتنا بجے ہیں؟ کیا آپ کے پاس گھڑی ہے؟', ARRAY['time', 'watch', 'clock', 'now', 'hour'], ARRAY['وقت', 'گھڑی', 'اب', 'بجے'], 'time', 'beginner', 'Time checking'),
('Are you hungry? Would you like to eat something?', 'کیا آپ بھوکے ہیں؟ کیا آپ کچھ کھانا چاہیں گے؟', ARRAY['hungry', 'eat', 'food', 'like', 'something'], ARRAY['بھوک', 'کھانا', 'کھانے', 'چاہیں', 'کچھ'], 'daily_life', 'beginner', 'Meal planning'),
('Do you like music? What kind of music do you prefer?', 'کیا آپ کو موسیقی پسند ہے؟ آپ کس قسم کی موسیقی پسند کرتے ہیں؟', ARRAY['music', 'like', 'kind', 'prefer', 'songs'], ARRAY['موسیقی', 'پسند', 'قسم', 'ترجیح', 'گانے'], 'preferences', 'beginner', 'Music discussion'),
('What''s your favorite color? Why do you like it?', 'آپ کا پسندیدہ رنگ کیا ہے؟ آپ اسے کیوں پسند کرتے ہیں؟', ARRAY['favorite', 'color', 'blue', 'like', 'why'], ARRAY['پسندیدہ', 'رنگ', 'نیلا', 'پسند', 'کیوں'], 'preferences', 'beginner', 'Color preference'),
('Can you help me? I need some assistance.', 'کیا آپ میری مدد کر سکتے ہیں؟ مجھے کچھ مدد چاہیے۔', ARRAY['help', 'assistance', 'need', 'can', 'sure'], ARRAY['مدد', 'سہولت', 'چاہیے', 'کر سکتے', 'یقیناً'], 'help', 'beginner', 'Asking for help'),
('Do you understand what I''m saying? Should I speak slowly?', 'کیا آپ سمجھتے ہیں جو میں کہہ رہا ہوں؟ کیا میں آہستہ بولوں؟', ARRAY['understand', 'saying', 'speak', 'slowly', 'clear'], ARRAY['سمجھتے', 'کہہ رہا', 'بول', 'آہستہ', 'صاف'], 'communication', 'beginner', 'Clarification request'),
('Is it raining outside? Should we take an umbrella?', 'کیا باہر بارش ہو رہی ہے؟ کیا ہمیں چھتری لینی چاہیے؟', ARRAY['raining', 'outside', 'umbrella', 'weather', 'wet'], ARRAY['بارش', 'باہر', 'چھتری', 'موسم', 'گیلا'], 'weather', 'beginner', 'Weather discussion'),
('Do you have brothers and sisters? How many siblings do you have?', 'کیا آپ کے بھائی بہن ہیں؟ آپ کے کتنے بہن بھائی ہیں؟', ARRAY['brothers', 'sisters', 'siblings', 'family', 'many'], ARRAY['بھائی', 'بہن', 'بہن بھائی', 'خاندان', 'کتنے'], 'family', 'beginner', 'Family discussion'),
('What do you like to eat? Do you prefer Pakistani food?', 'آپ کیا کھانا پسند کرتے ہیں؟ کیا آپ پاکستانی کھانا پسند کرتے ہیں؟', ARRAY['eat', 'food', 'Pakistani', 'prefer', 'like'], ARRAY['کھانا', 'کھانے', 'پاکستانی', 'پسند', 'ترجیح'], 'food', 'beginner', 'Food preferences'),
('Are you tired? Would you like to rest for a while?', 'کیا آپ تھکے ہوئے ہیں؟ کیا آپ تھوڑی دیر آرام کرنا چاہیں گے؟', ARRAY['tired', 'rest', 'sleep', 'while', 'feel'], ARRAY['تھکے', 'آرام', 'نیند', 'دیر', 'محسوس'], 'daily_life', 'beginner', 'Rest and relaxation'),
('Do you play sports? What sports do you enjoy?', 'کیا آپ کھیل کھیلتے ہیں؟ آپ کون سے کھیل پسند کرتے ہیں؟', ARRAY['play', 'sports', 'cricket', 'enjoy', 'games'], ARRAY['کھیلتے', 'کھیل', 'کرکٹ', 'پسند', 'گیمز'], 'activities', 'beginner', 'Sports discussion'),
('What''s the weather like today? Is it hot or cold?', 'آج موسم کیسا ہے؟ کیا گرم ہے یا ٹھنڈا؟', ARRAY['weather', 'today', 'hot', 'cold', 'temperature'], ARRAY['موسم', 'آج', 'گرم', 'ٹھنڈا', 'درجہ حرارت'], 'weather', 'beginner', 'Weather description'),
('Do you watch movies? What type of movies do you like?', 'کیا آپ فلمیں دیکھتے ہیں؟ آپ کس قسم کی فلمیں پسند کرتے ہیں؟', ARRAY['watch', 'movies', 'type', 'like', 'films'], ARRAY['دیکھتے', 'فلمیں', 'قسم', 'پسند', 'فلمز'], 'entertainment', 'beginner', 'Movie preferences'),
('What do you want to do in the future? Do you have any goals?', 'آپ مستقبل میں کیا کرنا چاہتے ہیں؟ کیا آپ کے کوئی اہداف ہیں؟', ARRAY['future', 'goals', 'want', 'do', 'plans'], ARRAY['مستقبل', 'اہداف', 'چاہتے', 'کرنا', 'منصوبے'], 'goals', 'beginner', 'Future planning');

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Indexes for Repeat After Me Phrases
CREATE INDEX IF NOT EXISTS idx_repeat_after_me_phrase ON public.ai_tutor_stage1_exercise1_repeat_after_me(phrase);
CREATE INDEX IF NOT EXISTS idx_repeat_after_me_urdu ON public.ai_tutor_stage1_exercise1_repeat_after_me(urdu_meaning);

-- Indexes for Quick Response Prompts
CREATE INDEX IF NOT EXISTS idx_quick_response_category ON public.ai_tutor_stage1_exercise2_quick_response(category);
CREATE INDEX IF NOT EXISTS idx_quick_response_difficulty ON public.ai_tutor_stage1_exercise2_quick_response(difficulty);
CREATE INDEX IF NOT EXISTS idx_quick_response_question ON public.ai_tutor_stage1_exercise2_quick_response(question);

-- Indexes for Functional Dialogue
CREATE INDEX IF NOT EXISTS idx_functional_dialogue_category ON public.ai_tutor_stage1_exercise3_functional_dialogue(category);
CREATE INDEX IF NOT EXISTS idx_functional_dialogue_difficulty ON public.ai_tutor_stage1_exercise3_functional_dialogue(difficulty);
CREATE INDEX IF NOT EXISTS idx_functional_dialogue_context ON public.ai_tutor_stage1_exercise3_functional_dialogue(context);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE public.ai_tutor_stage1_exercise1_repeat_after_me ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_tutor_stage1_exercise2_quick_response ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_tutor_stage1_exercise3_functional_dialogue ENABLE ROW LEVEL SECURITY;

-- RLS Policies for public access (these are content tables, not user-specific)
CREATE POLICY "Anyone can view repeat after me phrases" ON public.ai_tutor_stage1_exercise1_repeat_after_me FOR SELECT USING (true);
CREATE POLICY "Anyone can view quick response prompts" ON public.ai_tutor_stage1_exercise2_quick_response FOR SELECT USING (true);
CREATE POLICY "Anyone can view functional dialogue" ON public.ai_tutor_stage1_exercise3_functional_dialogue FOR SELECT USING (true);

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

-- Grant permissions for all tables
GRANT ALL ON public.ai_tutor_stage1_exercise1_repeat_after_me TO anon, authenticated;
GRANT ALL ON public.ai_tutor_stage1_exercise2_quick_response TO anon, authenticated;
GRANT ALL ON public.ai_tutor_stage1_exercise3_functional_dialogue TO anon, authenticated;

-- Grant permissions for sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Verify data insertion
SELECT 'Repeat After Me Phrases' as table_name, COUNT(*) as record_count FROM public.ai_tutor_stage1_exercise1_repeat_after_me
UNION ALL
SELECT 'Quick Response Prompts' as table_name, COUNT(*) as record_count FROM public.ai_tutor_stage1_exercise2_quick_response
UNION ALL
SELECT 'Functional Dialogue' as table_name, COUNT(*) as record_count FROM public.ai_tutor_stage1_exercise3_functional_dialogue;

-- Sample data verification
SELECT 'Sample Repeat After Me Phrases:' as info;
SELECT id, phrase, urdu_meaning FROM public.ai_tutor_stage1_exercise1_repeat_after_me LIMIT 3;

SELECT 'Sample Quick Response Prompts:' as info;
SELECT id, question, question_urdu, category FROM public.ai_tutor_stage1_exercise2_quick_response LIMIT 3;

SELECT 'Sample Functional Dialogue:' as info;
SELECT id, ai_prompt, ai_prompt_urdu, category FROM public.ai_tutor_stage1_exercise3_functional_dialogue LIMIT 3;



