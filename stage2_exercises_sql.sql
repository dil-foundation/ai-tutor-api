-- =============================================================================
-- AI English Tutor - Stage 2 Exercises Database Schema
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- STAGE 2 EXERCISE 1: DAILY ROUTINE NARRATION
-- =============================================================================

-- Table for Daily Routine Narration
CREATE TABLE IF NOT EXISTS public.ai_tutor_stage2_exercise1_daily_routine (
    id SERIAL PRIMARY KEY,
    phrase TEXT NOT NULL,
    phrase_urdu TEXT NOT NULL,
    example TEXT NOT NULL,
    example_urdu TEXT NOT NULL,
    keywords TEXT[] NOT NULL,
    keywords_urdu TEXT[] NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'a2_beginner',
    tense_focus TEXT NOT NULL,
    sentence_structure TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert data for Daily Routine Narration
INSERT INTO public.ai_tutor_stage2_exercise1_daily_routine (phrase, phrase_urdu, example, example_urdu, keywords, keywords_urdu, category, difficulty, tense_focus, sentence_structure) VALUES
('What time do you wake up and what do you do first?', 'آپ کس وقت اٹھتے ہیں اور سب سے پہلے کیا کرتے ہیں؟', 'I wake up at 6 a.m. and brush my teeth first.', 'میں صبح 6 بجے اٹھتا ہوں اور سب سے پہلے دانت صاف کرتا ہوں۔', ARRAY['wake up', 'brush teeth', 'morning', 'first'], ARRAY['اٹھتے', 'دانت صاف', 'صبح', 'پہلے'], 'morning_routine', 'a2_beginner', 'present_simple', 'time + action + sequence'),
('What do you usually have for breakfast?', 'آپ عام طور پر ناشتے میں کیا کھاتے ہیں؟', 'I usually eat eggs and toast for breakfast.', 'میں عام طور پر ناشتے میں انڈے اور ٹوسٹ کھاتا ہوں۔', ARRAY['breakfast', 'eggs', 'toast', 'eat', 'usually'], ARRAY['ناشتہ', 'انڈے', 'ٹوسٹ', 'کھاتے', 'عام طور پر'], 'morning_routine', 'a2_beginner', 'present_simple', 'frequency + food + meal'),
('How do you get to work or school?', 'آپ کام یا سکول کیسے جاتے ہیں؟', 'I take the bus to work every morning.', 'میں ہر صبح کام کے لیے بس لیتا ہوں۔', ARRAY['take', 'bus', 'work', 'school', 'every'], ARRAY['لیتے', 'بس', 'کام', 'سکول', 'ہر'], 'transportation', 'a2_beginner', 'present_simple', 'transport + destination + frequency'),
('What do you do during your lunch break?', 'آپ دوپہر کے کھانے کے وقفے میں کیا کرتے ہیں؟', 'I eat lunch with my colleagues and sometimes take a short walk.', 'میں اپنے ساتھیوں کے ساتھ دوپہر کا کھانا کھاتا ہوں اور کبھی کبھی تھوڑی سیر کرتا ہوں۔', ARRAY['lunch', 'colleagues', 'walk', 'break', 'sometimes'], ARRAY['دوپہر کا کھانا', 'ساتھی', 'سیر', 'وقفہ', 'کبھی کبھی'], 'work_routine', 'a2_intermediate', 'present_simple', 'action + people + additional_activity'),
('What time do you finish work or classes?', 'آپ کس وقت کام یا کلاسز ختم کرتے ہیں؟', 'I finish work at 5 p.m. and then go home.', 'میں شام 5 بجے کام ختم کرتا ہوں اور پھر گھر جاتا ہوں۔', ARRAY['finish', 'work', 'classes', 'home', 'then'], ARRAY['ختم', 'کام', 'کلاسز', 'گھر', 'پھر'], 'work_routine', 'a2_beginner', 'present_simple', 'time + action + sequence'),
('What do you do when you get home?', 'آپ گھر آنے کے بعد کیا کرتے ہیں؟', 'When I get home, I change my clothes and relax for a while.', 'جب میں گھر آتا ہوں تو اپنے کپڑے تبدیل کرتا ہوں اور تھوڑی دیر آرام کرتا ہوں۔', ARRAY['home', 'change', 'clothes', 'relax', 'while'], ARRAY['گھر', 'تبدیل', 'کپڑے', 'آرام', 'دیر'], 'evening_routine', 'a2_intermediate', 'present_simple', 'when + action + additional_action'),
('What do you usually have for dinner?', 'آپ عام طور پر رات کے کھانے میں کیا کھاتے ہیں؟', 'I usually have rice and curry for dinner with my family.', 'میں عام طور پر اپنے خاندان کے ساتھ رات کے کھانے میں چاول اور سالن کھاتا ہوں۔', ARRAY['dinner', 'rice', 'curry', 'family', 'usually'], ARRAY['رات کا کھانا', 'چاول', 'سالن', 'خاندان', 'عام طور پر'], 'evening_routine', 'a2_intermediate', 'present_simple', 'frequency + food + people'),
('What do you do in the evening before bed?', 'آپ سونے سے پہلے شام میں کیا کرتے ہیں؟', 'I watch TV, read a book, and then brush my teeth before bed.', 'میں ٹی وی دیکھتا ہوں، کتاب پڑھتا ہوں، اور پھر سونے سے پہلے دانت صاف کرتا ہوں۔', ARRAY['evening', 'watch', 'read', 'brush', 'before'], ARRAY['شام', 'دیکھتے', 'پڑھتے', 'صاف', 'پہلے'], 'evening_routine', 'a2_intermediate', 'present_simple', 'multiple_actions + sequence'),
('What time do you usually go to bed?', 'آپ عام طور پر کس وقت سوتے ہیں؟', 'I usually go to bed at 10 p.m. because I need to wake up early.', 'میں عام طور پر رات 10 بجے سوتا ہوں کیونکہ مجھے جلدی اٹھنا ہوتا ہے۔', ARRAY['bed', 'usually', 'because', 'early', 'need'], ARRAY['سونے', 'عام طور پر', 'کیونکہ', 'جلدی', 'ضرورت'], 'evening_routine', 'a2_intermediate', 'present_simple', 'time + reason + explanation'),
('What do you do on weekends?', 'آپ ہفتے کے آخر میں کیا کرتے ہیں؟', 'On weekends, I spend time with my family and sometimes go shopping.', 'ہفتے کے آخر میں، میں اپنے خاندان کے ساتھ وقت گزارتا ہوں اور کبھی کبھی خریداری کرتا ہوں۔', ARRAY['weekends', 'spend', 'family', 'shopping', 'sometimes'], ARRAY['ہفتے کے آخر', 'گزارتے', 'خاندان', 'خریداری', 'کبھی کبھی'], 'weekend_activities', 'a2_intermediate', 'present_simple', 'time_period + activity + additional_activity'),
('How often do you exercise or play sports?', 'آپ کتنی بار ورزش یا کھیل کھیلتے ہیں؟', 'I exercise three times a week and play cricket on Sundays.', 'میں ہفتے میں تین بار ورزش کرتا ہوں اور اتوار کو کرکٹ کھیلتا ہوں۔', ARRAY['exercise', 'sports', 'times', 'week', 'cricket'], ARRAY['ورزش', 'کھیل', 'بار', 'ہفتہ', 'کرکٹ'], 'health_activities', 'a2_intermediate', 'present_simple', 'frequency + activity + specific_day'),
('What do you do when you have free time?', 'آپ فارغ وقت میں کیا کرتے ہیں؟', 'When I have free time, I listen to music, read books, or call my friends.', 'جب میرے پاس فارغ وقت ہوتا ہے تو میں موسیقی سنتا ہوں، کتابیں پڑھتا ہوں، یا اپنے دوستوں کو فون کرتا ہوں۔', ARRAY['free time', 'listen', 'music', 'read', 'call'], ARRAY['فارغ وقت', 'سننا', 'موسیقی', 'پڑھنا', 'فون'], 'leisure_activities', 'a2_intermediate', 'present_simple', 'when + multiple_activities'),
('How do you prepare for work or school in the morning?', 'آپ صبح کام یا سکول کے لیے کیسے تیار ہوتے ہیں؟', 'I prepare by taking a shower, getting dressed, and having breakfast.', 'میں نہانے، کپڑے پہننے اور ناشتہ کرنے سے تیار ہوتا ہوں۔', ARRAY['prepare', 'shower', 'dressed', 'breakfast', 'morning'], ARRAY['تیار', 'نہانا', 'کپڑے', 'ناشتہ', 'صبح'], 'morning_routine', 'a2_intermediate', 'present_simple', 'action + multiple_preparations'),
('What do you do when you feel stressed or tired?', 'آپ جب تناؤ یا تھکاوٹ محسوس کرتے ہیں تو کیا کرتے ہیں؟', 'When I feel stressed, I take deep breaths and listen to calming music.', 'جب میں تناؤ محسوس کرتا ہوں تو گہری سانسیں لیتا ہوں اور پرسکون موسیقی سنتا ہوں۔', ARRAY['stressed', 'tired', 'breaths', 'calming', 'music'], ARRAY['تناؤ', 'تھکاوٹ', 'سانسیں', 'پرسکون', 'موسیقی'], 'wellness', 'a2_advanced', 'present_simple', 'when + feeling + coping_activities'),
('What do you usually do on holidays?', 'آپ عام طور پر چھٹیوں میں کیا کرتے ہیں؟', 'On holidays, I usually visit my family, travel to new places, or rest at home.', 'چھٹیوں میں، میں عام طور پر اپنے خاندان سے ملتا ہوں، نئی جگہوں پر سفر کرتا ہوں، یا گھر پر آرام کرتا ہوں۔', ARRAY['holidays', 'visit', 'family', 'travel', 'rest'], ARRAY['چھٹیاں', 'ملنا', 'خاندان', 'سفر', 'آرام'], 'holiday_activities', 'a2_advanced', 'present_simple', 'time_period + multiple_activities'),
('How do you manage your daily schedule?', 'آپ اپنے روزانہ کے شیڈول کو کیسے منظم کرتے ہیں؟', 'I manage my schedule by using a calendar and making a to-do list every morning.', 'میں اپنے شیڈول کو کیلنڈر استعمال کرنے اور ہر صبح کام کی فہرست بنانے سے منظم کرتا ہوں۔', ARRAY['manage', 'schedule', 'calendar', 'to-do list', 'morning'], ARRAY['منظم', 'شیڈول', 'کیلنڈر', 'فہرست', 'صبح'], 'organization', 'a2_advanced', 'present_simple', 'action + tools + frequency'),
('What do you do when you wake up late?', 'آپ جب دیر سے اٹھتے ہیں تو کیا کرتے ہیں؟', 'When I wake up late, I quickly get ready and skip breakfast to be on time.', 'جب میں دیر سے اٹھتا ہوں تو جلدی تیار ہوتا ہوں اور وقت پر پہنچنے کے لیے ناشتہ چھوڑ دیتا ہوں۔', ARRAY['late', 'quickly', 'ready', 'skip', 'breakfast'], ARRAY['دیر', 'جلدی', 'تیار', 'چھوڑنا', 'ناشتہ'], 'problem_solving', 'a2_advanced', 'present_simple', 'when + problem + solution'),
('What do you do to stay healthy?', 'آپ صحت مند رہنے کے لیے کیا کرتے ہیں؟', 'I stay healthy by exercising regularly, eating balanced meals, and getting enough sleep.', 'میں باقاعدگی سے ورزش کرنے، متوازن کھانا کھانے اور کافی نیند لینے سے صحت مند رہتا ہوں۔', ARRAY['healthy', 'exercise', 'balanced', 'meals', 'sleep'], ARRAY['صحت مند', 'ورزش', 'متوازن', 'کھانا', 'نیند'], 'health_activities', 'a2_advanced', 'present_simple', 'goal + multiple_activities'),
('How do you spend time with your family?', 'آپ اپنے خاندان کے ساتھ وقت کیسے گزارتے ہیں؟', 'I spend time with my family by having dinner together, watching movies, and talking about our day.', 'میں اپنے خاندان کے ساتھ وقت ایک ساتھ کھانا کھانے، فلمیں دیکھنے اور اپنے دن کے بارے میں بات کرنے سے گزارتا ہوں۔', ARRAY['family', 'dinner', 'movies', 'talking', 'together'], ARRAY['خاندان', 'کھانا', 'فلمیں', 'بات', 'ساتھ'], 'family_activities', 'a2_advanced', 'present_simple', 'people + multiple_activities'),
('What do you do to improve your English?', 'آپ اپنی انگریزی بہتر بنانے کے لیے کیا کرتے ہیں؟', 'I improve my English by practicing with this app, watching English movies, and reading books.', 'میں اپنی انگریزی اس ایپ کے ساتھ مشق کرنے، انگریزی فلمیں دیکھنے اور کتابیں پڑھنے سے بہتر بناتا ہوں۔', ARRAY['improve', 'English', 'practice', 'movies', 'reading'], ARRAY['بہتر', 'انگریزی', 'مشق', 'فلمیں', 'پڑھنا'], 'learning_activities', 'a2_advanced', 'present_simple', 'goal + multiple_methods');

-- =============================================================================
-- STAGE 2 EXERCISE 2: QUESTION ANSWER CHAT PRACTICE
-- =============================================================================

-- Table for Question Answer Chat Practice
CREATE TABLE IF NOT EXISTS public.ai_tutor_stage2_exercise2_question_answer (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    question_urdu TEXT NOT NULL,
    expected_answers TEXT[] NOT NULL,
    expected_answers_urdu TEXT[] NOT NULL,
    keywords TEXT[] NOT NULL,
    keywords_urdu TEXT[] NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'a2_beginner',
    tense TEXT NOT NULL,
    sentence_structure TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert data for Question Answer Chat Practice
INSERT INTO public.ai_tutor_stage2_exercise2_question_answer (question, question_urdu, expected_answers, expected_answers_urdu, keywords, keywords_urdu, category, difficulty, tense, sentence_structure) VALUES
('Where do you live and what do you like about your neighborhood?', 'آپ کہاں رہتے ہیں اور آپ کو اپنے محلے کے بارے میں کیا پسند ہے؟', ARRAY['I live in Karachi and I like the friendly people in my neighborhood.', 'I live in Lahore and I enjoy the parks and markets nearby.', 'I live in Islamabad and I love the peaceful environment here.'], ARRAY['میں کراچی میں رہتا ہوں اور مجھے اپنے محلے کے دوستانہ لوگ پسند ہیں۔', 'میں لاہور میں رہتا ہوں اور مجھے قریب کے پارکس اور مارکیٹس پسند ہیں۔', 'میں اسلام آباد میں رہتا ہوں اور مجھے یہاں کا پرسکون ماحول پسند ہے۔'], ARRAY['live', 'Karachi', 'Lahore', 'Islamabad', 'like', 'neighborhood', 'friendly', 'parks', 'peaceful'], ARRAY['رہتے', 'کراچی', 'لاہور', 'اسلام آباد', 'پسند', 'محلہ', 'دوستانہ', 'پارکس', 'پرسکون'], 'location_preferences', 'a2_beginner', 'present_simple', 'location + preference + reason'),
('What do you usually eat for lunch and why do you choose that food?', 'آپ عام طور پر دوپہر کے کھانے میں کیا کھاتے ہیں اور آپ وہ کھانا کیوں منتخب کرتے ہیں؟', ARRAY['I usually eat rice and curry for lunch because it''s healthy and filling.', 'I eat a sandwich for lunch because it''s quick and easy to prepare.', 'I have biryani for lunch because it''s my favorite Pakistani dish.'], ARRAY['میں عام طور پر دوپہر کے کھانے میں چاول اور سالن کھاتا ہوں کیونکہ یہ صحت مند اور پیٹ بھرنے والا ہے۔', 'میں دوپہر کے کھانے میں سینڈوچ کھاتا ہوں کیونکہ یہ تیز اور تیار کرنے میں آسان ہے۔', 'میں دوپہر کے کھانے میں بریانی کھاتا ہوں کیونکہ یہ میرا پسندیدہ پاکستانی کھانا ہے۔'], ARRAY['eat', 'lunch', 'rice', 'curry', 'sandwich', 'biryani', 'because', 'healthy', 'quick', 'favorite'], ARRAY['کھاتے', 'دوپہر کا کھانا', 'چاول', 'سالن', 'سینڈوچ', 'بریانی', 'کیونکہ', 'صحت مند', 'تیز', 'پسندیدہ'], 'food_preferences', 'a2_beginner', 'present_simple', 'food + reason + explanation'),
('How do you get to work or school and how long does it take?', 'آپ کام یا سکول کیسے جاتے ہیں اور اس میں کتنا وقت لگتا ہے؟', ARRAY['I take the bus to work and it takes about 30 minutes.', 'I drive my car to school and it takes 20 minutes.', 'I walk to work and it takes 15 minutes because I live nearby.'], ARRAY['میں کام کے لیے بس لیتا ہوں اور اس میں تقریباً 30 منٹ لگتے ہیں۔', 'میں سکول کے لیے اپنی گاڑی چلاتا ہوں اور اس میں 20 منٹ لگتے ہیں۔', 'میں کام کے لیے پیدل جاتا ہوں اور اس میں 15 منٹ لگتے ہیں کیونکہ میں قریب رہتا ہوں۔'], ARRAY['take', 'bus', 'drive', 'car', 'walk', 'minutes', 'because', 'nearby', 'work', 'school'], ARRAY['لیتے', 'بس', 'چلاتے', 'گاڑی', 'پیدل', 'منٹ', 'کیونکہ', 'قریب', 'کام', 'سکول'], 'transportation', 'a2_beginner', 'present_simple', 'transport + time + reason'),
('What do you do during your free time and why do you enjoy these activities?', 'آپ فارغ وقت میں کیا کرتے ہیں اور آپ کو یہ سرگرمیاں کیوں پسند ہیں؟', ARRAY['I read books and watch movies during my free time because they help me relax.', 'I play cricket and exercise because I enjoy sports and staying healthy.', 'I listen to music and call my friends because it makes me happy.'], ARRAY['میں فارغ وقت میں کتابیں پڑھتا ہوں اور فلمیں دیکھتا ہوں کیونکہ یہ مجھے آرام دینے میں مدد کرتے ہیں۔', 'میں کرکٹ کھیلتا ہوں اور ورزش کرتا ہوں کیونکہ مجھے کھیل اور صحت مند رہنا پسند ہے۔', 'میں موسیقی سنتا ہوں اور اپنے دوستوں کو فون کرتا ہوں کیونکہ یہ مجھے خوش کرتا ہے۔'], ARRAY['free time', 'read', 'watch', 'play', 'exercise', 'listen', 'call', 'because', 'relax', 'healthy', 'happy'], ARRAY['فارغ وقت', 'پڑھنا', 'دیکھنا', 'کھیلنا', 'ورزش', 'سننا', 'فون', 'کیونکہ', 'آرام', 'صحت مند', 'خوش'], 'leisure_activities', 'a2_intermediate', 'present_simple', 'activities + reason + benefit'),
('How often do you exercise and what types of exercise do you prefer?', 'آپ کتنی بار ورزش کرتے ہیں اور آپ کس قسم کی ورزش پسند کرتے ہیں؟', ARRAY['I exercise three times a week and I prefer running and swimming.', 'I exercise daily and I enjoy playing cricket and doing yoga.', 'I exercise twice a week and I like walking and cycling.'], ARRAY['میں ہفتے میں تین بار ورزش کرتا ہوں اور مجھے دوڑنا اور تیراکی پسند ہے۔', 'میں روزانہ ورزش کرتا ہوں اور مجھے کرکٹ کھیلنا اور یوگا کرنا پسند ہے۔', 'میں ہفتے میں دو بار ورزش کرتا ہوں اور مجھے پیدل چلنا اور سائیکل چلانا پسند ہے۔'], ARRAY['exercise', 'times', 'week', 'daily', 'twice', 'prefer', 'running', 'swimming', 'cricket', 'yoga', 'walking', 'cycling'], ARRAY['ورزش', 'بار', 'ہفتہ', 'روزانہ', 'دو بار', 'پسند', 'دوڑنا', 'تیراکی', 'کرکٹ', 'یوگا', 'پیدل چلنا', 'سائیکل'], 'health_activities', 'a2_intermediate', 'present_simple', 'frequency + activities + preferences'),
('What do you usually do on weekends and who do you spend time with?', 'آپ عام طور پر ہفتے کے آخر میں کیا کرتے ہیں اور آپ کس کے ساتھ وقت گزارتے ہیں؟', ARRAY['I usually visit my family on weekends and we have dinner together.', 'I spend time with my friends on weekends and we go shopping or watch movies.', 'I relax at home on weekends and spend time with my children.'], ARRAY['میں عام طور پر ہفتے کے آخر میں اپنے خاندان سے ملتا ہوں اور ہم ایک ساتھ کھانا کھاتے ہیں۔', 'میں ہفتے کے آخر میں اپنے دوستوں کے ساتھ وقت گزارتا ہوں اور ہم خریداری کرتے ہیں یا فلمیں دیکھتے ہیں۔', 'میں ہفتے کے آخر میں گھر پر آرام کرتا ہوں اور اپنے بچوں کے ساتھ وقت گزارتا ہوں۔'], ARRAY['weekends', 'visit', 'family', 'friends', 'spend', 'dinner', 'shopping', 'movies', 'relax', 'children'], ARRAY['ہفتے کے آخر', 'ملنا', 'خاندان', 'دوست', 'گزارنا', 'کھانا', 'خریداری', 'فلمیں', 'آرام', 'بچے'], 'weekend_activities', 'a2_intermediate', 'present_simple', 'time_period + activities + people'),
('How do you manage stress and what helps you feel better?', 'آپ تناؤ کو کیسے منظم کرتے ہیں اور آپ کو بہتر محسوس کرنے میں کیا مدد کرتا ہے؟', ARRAY['I manage stress by taking deep breaths and listening to calming music.', 'I exercise regularly and talk to my friends when I feel stressed.', 'I practice meditation and spend time in nature to feel better.'], ARRAY['میں تناؤ کو گہری سانسیں لینے اور پرسکون موسیقی سننے سے منظم کرتا ہوں۔', 'میں باقاعدگی سے ورزش کرتا ہوں اور جب میں تناؤ محسوس کرتا ہوں تو اپنے دوستوں سے بات کرتا ہوں۔', 'میں مراقبہ کرتا ہوں اور بہتر محسوس کرنے کے لیے فطرت میں وقت گزارتا ہوں۔'], ARRAY['manage', 'stress', 'deep breaths', 'calming', 'music', 'exercise', 'talk', 'meditation', 'nature', 'better'], ARRAY['منظم', 'تناؤ', 'گہری سانسیں', 'پرسکون', 'موسیقی', 'ورزش', 'بات', 'مراقبہ', 'فطرت', 'بہتر'], 'wellness', 'a2_intermediate', 'present_simple', 'problem + solution + benefit'),
('What do you do when you have a problem and how do you solve it?', 'آپ جب کوئی مسئلہ ہوتا ہے تو کیا کرتے ہیں اور آپ اسے کیسے حل کرتے ہیں؟', ARRAY['When I have a problem, I think about it carefully and ask for advice from family.', 'I discuss the problem with my friends and try to find the best solution.', 'I research the problem online and then make a plan to solve it.'], ARRAY['جب میرے پاس کوئی مسئلہ ہوتا ہے تو میں اس کے بارے میں غور کرتا ہوں اور خاندان سے مشورہ مانگتا ہوں۔', 'میں مسئلے پر اپنے دوستوں سے بات کرتا ہوں اور بہترین حل تلاش کرنے کی کوشش کرتا ہوں۔', 'میں مسئلے پر آن لائن تحقیق کرتا ہوں اور پھر اسے حل کرنے کا منصوبہ بناتا ہوں۔'], ARRAY['problem', 'think', 'carefully', 'advice', 'family', 'discuss', 'friends', 'solution', 'research', 'plan'], ARRAY['مسئلہ', 'غور', 'احتیاط سے', 'مشورہ', 'خاندان', 'بات', 'دوست', 'حل', 'تحقیق', 'منصوبہ'], 'problem_solving', 'a2_advanced', 'present_simple', 'when + problem + approach + method'),
('How do you stay organized and what tools do you use?', 'آپ منظم کیسے رہتے ہیں اور آپ کون سے اوزار استعمال کرتے ہیں؟', ARRAY['I stay organized by using a calendar and making to-do lists every day.', 'I use my phone''s reminder app and keep a notebook for important tasks.', 'I organize my workspace and use digital tools to track my schedule.'], ARRAY['میں کیلنڈر استعمال کرنے اور ہر روز کام کی فہرست بنانے سے منظم رہتا ہوں۔', 'میں اپنے فون کی یاد دہانی ایپ استعمال کرتا ہوں اور اہم کاموں کے لیے نوٹ بک رکھتا ہوں۔', 'میں اپنا کام کی جگہ منظم کرتا ہوں اور اپنے شیڈول کو ٹریک کرنے کے لیے ڈیجیٹل اوزار استعمال کرتا ہوں۔'], ARRAY['organized', 'calendar', 'to-do lists', 'reminder', 'notebook', 'workspace', 'digital', 'tools', 'schedule'], ARRAY['منظم', 'کیلنڈر', 'فہرست', 'یاد دہانی', 'نوٹ بک', 'کام کی جگہ', 'ڈیجیٹل', 'اوزار', 'شیڈول'], 'organization', 'a2_advanced', 'present_simple', 'method + tools + frequency'),
('What do you do to improve your skills and why is it important?', 'آپ اپنی مہارتوں کو بہتر بنانے کے لیے کیا کرتے ہیں اور یہ کیوں اہم ہے؟', ARRAY['I practice regularly and take online courses to improve my skills because it helps my career.', 'I read books and attend workshops to learn new things because knowledge is important.', 'I work on projects and seek feedback to improve because I want to grow professionally.'], ARRAY['میں باقاعدگی سے مشق کرتا ہوں اور اپنی مہارتوں کو بہتر بنانے کے لیے آن لائن کورسز لیتا ہوں کیونکہ یہ میری کیریئر میں مدد کرتا ہے۔', 'میں نئی چیزیں سیکھنے کے لیے کتابیں پڑھتا ہوں اور ورکشاپس میں شرکت کرتا ہوں کیونکہ علم اہم ہے۔', 'میں منصوبوں پر کام کرتا ہوں اور بہتر بننے کے لیے فیڈبیک مانگتا ہوں کیونکہ میں پیشہ ورانہ طور پر ترقی کرنا چاہتا ہوں۔'], ARRAY['improve', 'skills', 'practice', 'courses', 'career', 'read', 'workshops', 'knowledge', 'projects', 'feedback', 'grow'], ARRAY['بہتر', 'مہارتیں', 'مشق', 'کورسز', 'کیریئر', 'پڑھنا', 'ورکشاپس', 'علم', 'منصوبے', 'فیڈبیک', 'ترقی'], 'skill_development', 'a2_advanced', 'present_simple', 'activities + methods + importance'),
('How do you handle difficult situations and what have you learned from them?', 'آپ مشکل حالات کو کیسے سنبھالتے ہیں اور آپ نے ان سے کیا سیکھا ہے؟', ARRAY['I stay calm and think logically when facing difficult situations, and I''ve learned to be patient.', 'I ask for help from experienced people and I''ve learned that teamwork is important.', 'I break problems into smaller parts and I''ve learned that persistence leads to success.'], ARRAY['میں مشکل حالات کا سامنا کرتے وقت پرسکون رہتا ہوں اور منطقی طور پر سوچتا ہوں، اور میں نے صبر کرنا سیکھا ہے۔', 'میں تجربہ کار لوگوں سے مدد مانگتا ہوں اور میں نے سیکھا ہے کہ ٹیم ورک اہم ہے۔', 'میں مسائل کو چھوٹے حصوں میں تقسیم کرتا ہوں اور میں نے سیکھا ہے کہ ثابت قدمی کامیابی کی طرف لے جاتی ہے۔'], ARRAY['handle', 'difficult', 'situations', 'calm', 'logically', 'learned', 'patient', 'help', 'teamwork', 'persistence', 'success'], ARRAY['سنبھالنا', 'مشکل', 'حالات', 'پرسکون', 'منطقی', 'سیکھا', 'صبر', 'مدد', 'ٹیم ورک', 'ثابت قدمی', 'کامیابی'], 'life_lessons', 'a2_advanced', 'present_simple', 'approach + method + learning'),
('What do you do to maintain good relationships with family and friends?', 'آپ خاندان اور دوستوں کے ساتھ اچھے تعلقات برقرار رکھنے کے لیے کیا کرتے ہیں؟', ARRAY['I call my family regularly and spend quality time with friends to maintain good relationships.', 'I listen carefully to their problems and offer support when they need help.', 'I remember important dates and show appreciation for their presence in my life.'], ARRAY['میں اپنے خاندان کو باقاعدگی سے فون کرتا ہوں اور اچھے تعلقات برقرار رکھنے کے لیے دوستوں کے ساتھ معیاری وقت گزارتا ہوں۔', 'میں ان کے مسائل کو غور سے سنتا ہوں اور جب انہیں مدد کی ضرورت ہو تو تعاون پیش کرتا ہوں۔', 'میں اہم تاریخوں کو یاد رکھتا ہوں اور اپنی زندگی میں ان کی موجودگی کی تعریف کرتا ہوں۔'], ARRAY['maintain', 'relationships', 'family', 'friends', 'call', 'quality time', 'listen', 'support', 'remember', 'appreciation'], ARRAY['برقرار', 'تعلقات', 'خاندان', 'دوست', 'فون', 'معیاری وقت', 'سننا', 'تعاون', 'یاد', 'تعریف'], 'relationships', 'a2_advanced', 'present_simple', 'actions + people + purpose'),
('How do you plan for the future and what are your goals?', 'آپ مستقبل کے لیے کیسے منصوبہ بناتے ہیں اور آپ کے اہداف کیا ہیں؟', ARRAY['I set short-term and long-term goals and work towards them step by step.', 'I save money regularly and invest in my education to secure my future.', 'I develop new skills and build a network of contacts for career growth.'], ARRAY['میں مختصر مدت اور طویل مدت کے اہداف طے کرتا ہوں اور ان کی طرف قدم بہ قدم کام کرتا ہوں۔', 'میں باقاعدگی سے پیسے بچاتا ہوں اور اپنے مستقبل کو محفوظ بنانے کے لیے تعلیم میں سرمایہ کاری کرتا ہوں۔', 'میں نئی مہارتیں تیار کرتا ہوں اور کیریئر کی ترقی کے لیے رابطوں کا نیٹ ورک بناتا ہوں۔'], ARRAY['plan', 'future', 'goals', 'short-term', 'long-term', 'save', 'invest', 'education', 'skills', 'network', 'career'], ARRAY['منصوبہ', 'مستقبل', 'اہداف', 'مختصر مدت', 'طویل مدت', 'بچانا', 'سرمایہ کاری', 'تعلیم', 'مہارتیں', 'نیٹ ورک', 'کیریئر'], 'future_planning', 'a2_advanced', 'present_simple', 'planning + methods + objectives'),
('What do you do to stay motivated and how do you overcome challenges?', 'آپ حوصلہ برقرار رکھنے کے لیے کیا کرتے ہیں اور آپ چیلنجز کو کیسے عبور کرتے ہیں؟', ARRAY['I stay motivated by setting achievable goals and celebrating small successes.', 'I overcome challenges by staying positive and learning from my mistakes.', 'I maintain motivation by surrounding myself with supportive people and focusing on progress.'], ARRAY['میں قابل حصول اہداف طے کرنے اور چھوٹی کامیابیوں کا جشن منانے سے حوصلہ برقرار رکھتا ہوں۔', 'میں مثبت رہنے اور اپنی غلطیوں سے سیکھنے سے چیلنجز کو عبور کرتا ہوں۔', 'میں خود کو معاون لوگوں کے ساتھ رکھنے اور ترقی پر توجہ مرکوز کرنے سے حوصلہ برقرار رکھتا ہوں۔'], ARRAY['motivated', 'goals', 'successes', 'overcome', 'challenges', 'positive', 'mistakes', 'supportive', 'progress'], ARRAY['حوصلہ', 'اہداف', 'کامیابیاں', 'عبور', 'چیلنجز', 'مثبت', 'غلطیاں', 'معاون', 'ترقی'], 'motivation', 'a2_advanced', 'present_simple', 'motivation + methods + outcomes'),
('How do you contribute to your community and what impact do you want to make?', 'آپ اپنی کمیونٹی میں کیسے حصہ ڈالتے ہیں اور آپ کیا اثر چاہتے ہیں؟', ARRAY['I volunteer at local events and help neighbors when they need assistance.', 'I participate in community projects and want to make a positive difference.', 'I share my skills with others and hope to inspire people to help each other.'], ARRAY['میں مقامی تقریبات میں رضاکارانہ کام کرتا ہوں اور پڑوسیوں کی مدد کرتا ہوں جب انہیں ضرورت ہو۔', 'میں کمیونٹی کے منصوبوں میں حصہ لیتا ہوں اور مثبت فرق پیدا کرنا چاہتا ہوں۔', 'میں اپنی مہارتیں دوسروں کے ساتھ شیئر کرتا ہوں اور امید کرتا ہوں کہ لوگوں کو ایک دوسرے کی مدد کرنے کی ترغیب دوں۔'], ARRAY['contribute', 'community', 'volunteer', 'help', 'participate', 'projects', 'positive', 'difference', 'share', 'inspire'], ARRAY['حصہ ڈالنا', 'کمیونٹی', 'رضاکار', 'مدد', 'حصہ لینا', 'منصوبے', 'مثبت', 'فرق', 'شیئر', 'ترغیب'], 'community_service', 'a2_advanced', 'present_simple', 'contribution + activities + impact');

-- =============================================================================
-- STAGE 2 EXERCISE 3: ROLEPLAY SIMULATION
-- =============================================================================

-- Table for Roleplay Simulation
CREATE TABLE IF NOT EXISTS public.ai_tutor_stage2_exercise3_roleplay (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    title_urdu TEXT NOT NULL,
    description TEXT NOT NULL,
    description_urdu TEXT NOT NULL,
    initial_prompt TEXT NOT NULL,
    initial_prompt_urdu TEXT NOT NULL,
    scenario_context TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'a2_beginner',
    expected_keywords TEXT[] NOT NULL,
    expected_keywords_urdu TEXT[] NOT NULL,
    ai_character TEXT NOT NULL,
    conversation_flow TEXT NOT NULL,
    cultural_context TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert data for Roleplay Simulation
INSERT INTO public.ai_tutor_stage2_exercise3_roleplay (title, title_urdu, description, description_urdu, initial_prompt, initial_prompt_urdu, scenario_context, difficulty, expected_keywords, expected_keywords_urdu, ai_character, conversation_flow, cultural_context) VALUES
('Order Food at a Restaurant', 'ریستوران میں کھانا آرڈر کرنا', 'Practice ordering food at a restaurant with natural conversation flow.', 'قدرتی گفتگو کے ساتھ ریستوران میں کھانا آرڈر کرنے کی مشق کریں۔', 'You are at a restaurant. The waiter asks: ''What would you like to eat?''', 'آپ ریستوران میں ہیں۔ ویٹر پوچھتا ہے: ''آپ کیا کھانا چاہیں گے؟''', 'restaurant_ordering', 'a2_beginner', ARRAY['like', 'eat', 'food', 'menu', 'order', 'please'], ARRAY['پسند', 'کھانا', 'کھانے', 'مینو', 'آرڈر', 'براہ کرم'], 'waiter', 'order_food', 'pakistani_restaurant'),
('Visit a Doctor', 'ڈاکٹر سے ملاقات', 'Simulate a doctor visit conversation with medical symptoms and advice.', 'طبی علامات اور مشورے کے ساتھ ڈاکٹر سے ملاقات کی گفتگو کی مشق کریں۔', 'You are visiting a doctor. The doctor says: ''What brings you in today?''', 'آپ ڈاکٹر سے ملنے گئے ہیں۔ ڈاکٹر کہتا ہے: ''آج آپ کو کیا مسئلہ ہے؟''', 'medical_consultation', 'a2_beginner', ARRAY['feel', 'pain', 'sick', 'symptoms', 'problem', 'doctor'], ARRAY['محسوس', 'درد', 'بیمار', 'علامات', 'مسئلہ', 'ڈاکٹر'], 'doctor', 'medical_consultation', 'pakistani_healthcare'),
('Buy a Bus Ticket', 'بس کا ٹکٹ خریدنے', 'Purchase a bus ticket at a bus station with route and schedule information.', 'روٹ اور شیڈول کی معلومات کے ساتھ بس اسٹیشن سے ٹکٹ خریدنے کی مشق کریں۔', 'The clerk asks: ''Where do you want to go?''', 'کلرک پوچھتا ہے: ''آپ کہاں جانا چاہتے ہیں؟''', 'transportation_booking', 'a2_beginner', ARRAY['go', 'destination', 'ticket', 'bus', 'time', 'price'], ARRAY['جانا', 'منزل', 'ٹکٹ', 'بس', 'وقت', 'قیمت'], 'ticket_clerk', 'transportation_booking', 'pakistani_transport'),
('Shop for Clothes', 'کپڑے خریدنے', 'Browse and purchase clothing items with size and style preferences.', 'سائز اور اسٹائل کی ترجیحات کے ساتھ کپڑے دیکھنے اور خریدنے کی مشق کریں۔', 'The shop assistant asks: ''Can I help you find something?''', 'شاپ اسسٹنٹ پوچھتا ہے: ''کیا میں آپ کو کچھ تلاش کرنے میں مدد کر سکتا ہوں؟''', 'clothing_shopping', 'a2_intermediate', ARRAY['clothes', 'size', 'color', 'style', 'try', 'fit'], ARRAY['کپڑے', 'سائز', 'رنگ', 'اسٹائل', 'آزمائیں', 'فٹ'], 'shop_assistant', 'clothing_shopping', 'pakistani_fashion'),
('Book a Hotel Room', 'ہوٹل کا کمرہ بک کرنا', 'Reserve a hotel room with accommodation preferences and dates.', 'رہائش کی ترجیحات اور تاریخوں کے ساتھ ہوٹل کا کمرہ ریزرو کرنے کی مشق کریں۔', 'The receptionist asks: ''How can I help you with your booking?''', 'ریسپشنسٹ پوچھتا ہے: ''میں آپ کی بکنگ میں کیسے مدد کر سکتا ہوں؟''', 'hotel_booking', 'a2_intermediate', ARRAY['room', 'booking', 'dates', 'nights', 'price', 'available'], ARRAY['کمرہ', 'بکنگ', 'تاریخیں', 'راتیں', 'قیمت', 'دستیاب'], 'receptionist', 'hotel_booking', 'pakistani_hospitality'),
('Ask for Directions', 'راستہ پوچھنا', 'Ask for and receive directions to a specific location in the city.', 'شہر میں کسی خاص جگہ کا راستہ پوچھنے اور حاصل کرنے کی مشق کریں۔', 'A local person asks: ''Do you need help finding something?''', 'ایک مقامی شخص پوچھتا ہے: ''کیا آپ کو کچھ تلاش کرنے میں مدد چاہیے؟''', 'asking_directions', 'a2_intermediate', ARRAY['find', 'location', 'directions', 'street', 'near', 'far'], ARRAY['تلاش', 'مقام', 'راستہ', 'گلی', 'قریب', 'دور'], 'local_person', 'asking_directions', 'pakistani_city'),
('Order Coffee at a Cafe', 'کیفے میں کافی آرڈر کرنا', 'Order coffee and snacks at a cafe with customization preferences.', 'ترجیحات کی تخصیص کے ساتھ کیفے میں کافی اور سنیکس آرڈر کرنے کی مشق کریں۔', 'The barista asks: ''What would you like to drink?''', 'بارسٹا پوچھتا ہے: ''آپ کیا پینا چاہیں گے؟''', 'cafe_ordering', 'a2_intermediate', ARRAY['coffee', 'drink', 'size', 'hot', 'cold', 'sugar'], ARRAY['کافی', 'پینا', 'سائز', 'گرم', 'ٹھنڈا', 'چینی'], 'barista', 'cafe_ordering', 'modern_cafe'),
('Report a Problem', 'مسئلہ رپورٹ کرنا', 'Report a problem or complaint to customer service.', 'کسٹمر سروس کو مسئلہ یا شکایت رپورٹ کرنے کی مشق کریں۔', 'The customer service representative asks: ''How can I help you today?''', 'کسٹمر سروس نمائندہ پوچھتا ہے: ''میں آج آپ کی کیسے مدد کر سکتا ہوں؟''', 'customer_service', 'a2_intermediate', ARRAY['problem', 'issue', 'complaint', 'help', 'solve', 'service'], ARRAY['مسئلہ', 'معاملہ', 'شکایت', 'مدد', 'حل', 'سروس'], 'customer_service_rep', 'problem_reporting', 'pakistani_service'),
('Make a Phone Call', 'فون کال کرنا', 'Make a phone call to schedule an appointment or get information.', 'ملاقات کا وقت طے کرنے یا معلومات حاصل کرنے کے لیے فون کال کرنے کی مشق کریں۔', 'The person answers: ''Hello, how can I help you?''', 'شخص جواب دیتا ہے: ''ہیلو، میں آپ کی کیسے مدد کر سکتا ہوں؟''', 'phone_conversation', 'a2_intermediate', ARRAY['call', 'appointment', 'information', 'available', 'time', 'speak'], ARRAY['کال', 'ملاقات', 'معلومات', 'دستیاب', 'وقت', 'بات'], 'phone_operator', 'phone_conversation', 'pakistani_communication'),
('Apply for a Job', 'نوکری کے لیے درخواست', 'Apply for a job position with qualifications and experience discussion.', 'قابلیتوں اور تجربے کی گفتگو کے ساتھ نوکری کے عہدے کے لیے درخواست دینے کی مشق کریں۔', 'The interviewer asks: ''Tell me about your experience and qualifications.''', 'انٹرویو لینے والا پوچھتا ہے: ''مجھے اپنے تجربے اور قابلیتوں کے بارے میں بتائیں۔''', 'job_interview', 'a2_advanced', ARRAY['experience', 'qualifications', 'work', 'skills', 'education', 'job'], ARRAY['تجربہ', 'قابلیتیں', 'کام', 'مہارتیں', 'تعلیم', 'نوکری'], 'interviewer', 'job_interview', 'pakistani_workplace'),
('Order Groceries Online', 'آن لائن گروسری آرڈر کرنا', 'Order groceries online with delivery preferences and payment options.', 'ترسیل کی ترجیحات اور ادائیگی کے اختیارات کے ساتھ آن لائن گروسری آرڈر کرنے کی مشق کریں۔', 'The online assistant asks: ''What items would you like to order today?''', 'آن لائن اسسٹنٹ پوچھتا ہے: ''آپ آج کون سی اشیاء آرڈر کرنا چاہیں گے؟''', 'online_shopping', 'a2_advanced', ARRAY['order', 'items', 'delivery', 'payment', 'address', 'total'], ARRAY['آرڈر', 'اشیاء', 'ترسیل', 'ادائیگی', 'پتہ', 'کل'], 'online_assistant', 'online_shopping', 'modern_shopping'),
('Discuss Weather and Plans', 'موسم اور منصوبوں پر بات چیت', 'Discuss weather conditions and how they affect daily plans.', 'موسمی حالات اور ان کے روزانہ کے منصوبوں پر اثرات پر بات چیت کی مشق کریں۔', 'A friend asks: ''What''s the weather like today and what are your plans?''', 'ایک دوست پوچھتا ہے: ''آج موسم کیسا ہے اور آپ کے کیا منصوبے ہیں؟''', 'weather_discussion', 'a2_advanced', ARRAY['weather', 'plans', 'rain', 'sunny', 'change', 'activities'], ARRAY['موسم', 'منصوبے', 'بارش', 'دھوپ', 'تبدیلی', 'سرگرمیاں'], 'friend', 'weather_discussion', 'pakistani_weather'),
('Book a Flight', 'ہوائی جہاز کا ٹکٹ بک کرنا', 'Book a flight with travel dates, destination, and seating preferences.', 'سفر کی تاریخوں، منزل اور نشست کی ترجیحات کے ساتھ ہوائی جہاز کا ٹکٹ بک کرنے کی مشق کریں۔', 'The travel agent asks: ''Where would you like to travel and when?''', 'ٹریول ایجنٹ پوچھتا ہے: ''آپ کہاں سفر کرنا چاہتے ہیں اور کب؟''', 'flight_booking', 'a2_advanced', ARRAY['travel', 'destination', 'dates', 'flight', 'seat', 'price'], ARRAY['سفر', 'منزل', 'تاریخیں', 'پرواز', 'نشست', 'قیمت'], 'travel_agent', 'flight_booking', 'pakistani_travel'),
('Discuss Family and Relationships', 'خاندان اور تعلقات پر بات چیت', 'Discuss family members, relationships, and personal connections.', 'خاندان کے ارکان، تعلقات اور ذاتی روابط پر بات چیت کی مشق کریں۔', 'A colleague asks: ''Tell me about your family and how you spend time together.''', 'ایک ساتھی پوچھتا ہے: ''مجھے اپنے خاندان کے بارے میں بتائیں اور آپ ایک ساتھ وقت کیسے گزارتے ہیں۔''', 'family_discussion', 'a2_advanced', ARRAY['family', 'relationships', 'spend', 'time', 'together', 'love'], ARRAY['خاندان', 'تعلقات', 'گزارنا', 'وقت', 'ساتھ', 'محبت'], 'colleague', 'family_discussion', 'pakistani_family'),
('Plan a Social Event', 'سماجی تقریب کی منصوبہ بندی', 'Plan a social event with friends including venue, food, and activities.', 'مقام، کھانا اور سرگرمیوں سمیت دوستوں کے ساتھ سماجی تقریب کی منصوبہ بندی کی مشق کریں۔', 'A friend asks: ''What should we do for our next get-together?''', 'ایک دوست پوچھتا ہے: ''ہماری اگلی ملاقات کے لیے ہمیں کیا کرنا چاہیے؟''', 'event_planning', 'a2_advanced', ARRAY['event', 'plan', 'venue', 'food', 'activities', 'friends'], ARRAY['تقریب', 'منصوبہ', 'مقام', 'کھانا', 'سرگرمیاں', 'دوست'], 'friend', 'event_planning', 'pakistani_social');

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Indexes for Daily Routine Narration
CREATE INDEX IF NOT EXISTS idx_daily_routine_category ON public.ai_tutor_stage2_exercise1_daily_routine(category);
CREATE INDEX IF NOT EXISTS idx_daily_routine_difficulty ON public.ai_tutor_stage2_exercise1_daily_routine(difficulty);
CREATE INDEX IF NOT EXISTS idx_daily_routine_tense ON public.ai_tutor_stage2_exercise1_daily_routine(tense_focus);

-- Indexes for Question Answer Chat Practice
CREATE INDEX IF NOT EXISTS idx_question_answer_category ON public.ai_tutor_stage2_exercise2_question_answer(category);
CREATE INDEX IF NOT EXISTS idx_question_answer_difficulty ON public.ai_tutor_stage2_exercise2_question_answer(difficulty);
CREATE INDEX IF NOT EXISTS idx_question_answer_tense ON public.ai_tutor_stage2_exercise2_question_answer(tense);

-- Indexes for Roleplay Simulation
CREATE INDEX IF NOT EXISTS idx_roleplay_scenario ON public.ai_tutor_stage2_exercise3_roleplay(scenario_context);
CREATE INDEX IF NOT EXISTS idx_roleplay_difficulty ON public.ai_tutor_stage2_exercise3_roleplay(difficulty);
CREATE INDEX IF NOT EXISTS idx_roleplay_character ON public.ai_tutor_stage2_exercise3_roleplay(ai_character);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE public.ai_tutor_stage2_exercise1_daily_routine ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_tutor_stage2_exercise2_question_answer ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_tutor_stage2_exercise3_roleplay ENABLE ROW LEVEL SECURITY;

-- RLS Policies for public access (these are content tables, not user-specific)
CREATE POLICY "Anyone can view daily routine narration" ON public.ai_tutor_stage2_exercise1_daily_routine FOR SELECT USING (true);
CREATE POLICY "Anyone can view question answer chat practice" ON public.ai_tutor_stage2_exercise2_question_answer FOR SELECT USING (true);
CREATE POLICY "Anyone can view roleplay simulation" ON public.ai_tutor_stage2_exercise3_roleplay FOR SELECT USING (true);

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

-- Grant permissions for all tables
GRANT ALL ON public.ai_tutor_stage2_exercise1_daily_routine TO anon, authenticated;
GRANT ALL ON public.ai_tutor_stage2_exercise2_question_answer TO anon, authenticated;
GRANT ALL ON public.ai_tutor_stage2_exercise3_roleplay TO anon, authenticated;

-- Grant permissions for sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Verify data insertion
SELECT 'Daily Routine Narration' as table_name, COUNT(*) as record_count FROM public.ai_tutor_stage2_exercise1_daily_routine
UNION ALL
SELECT 'Question Answer Chat Practice' as table_name, COUNT(*) as record_count FROM public.ai_tutor_stage2_exercise2_question_answer
UNION ALL
SELECT 'Roleplay Simulation' as table_name, COUNT(*) as record_count FROM public.ai_tutor_stage2_exercise3_roleplay;

-- Sample data verification
SELECT 'Sample Daily Routine Narration:' as info;
SELECT id, phrase, phrase_urdu, category FROM public.ai_tutor_stage2_exercise1_daily_routine LIMIT 3;

SELECT 'Sample Question Answer Chat Practice:' as info;
SELECT id, question, question_urdu, category FROM public.ai_tutor_stage2_exercise2_question_answer LIMIT 3;

SELECT 'Sample Roleplay Simulation:' as info;
SELECT id, title, title_urdu, scenario_context FROM public.ai_tutor_stage2_exercise3_roleplay LIMIT 3;
