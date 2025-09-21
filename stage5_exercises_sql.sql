-- =============================================================================
-- AI English Tutor - Stage 5 Exercises Database Schema
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- STAGE 5 EXERCISE 1: ADVANCED DEBATE & ARGUMENTATION
-- =============================================================================

-- Table for Advanced Debate & Argumentation
CREATE TABLE IF NOT EXISTS public.ai_tutor_stage5_exercise1_advanced_debate (
    id SERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    topic_urdu TEXT NOT NULL,
    ai_position TEXT NOT NULL,
    ai_position_urdu TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'C1',
    speaking_duration TEXT NOT NULL,
    thinking_time TEXT NOT NULL,
    expected_structure TEXT NOT NULL,
    expected_keywords TEXT[] NOT NULL,
    expected_keywords_urdu TEXT[] NOT NULL,
    vocabulary_focus TEXT[] NOT NULL,
    vocabulary_focus_urdu TEXT[] NOT NULL,
    model_response TEXT NOT NULL,
    model_response_urdu TEXT NOT NULL,
    evaluation_criteria JSONB NOT NULL,
    learning_objectives TEXT[] NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert data for Advanced Debate & Argumentation
INSERT INTO public.ai_tutor_stage5_exercise1_advanced_debate (topic, topic_urdu, ai_position, ai_position_urdu, category, difficulty, speaking_duration, thinking_time, expected_structure, expected_keywords, expected_keywords_urdu, vocabulary_focus, vocabulary_focus_urdu, model_response, model_response_urdu, evaluation_criteria, learning_objectives) VALUES
('Should artificial intelligence be used in education?', 'کیا مصنوعی ذہانت کو تعلیم میں استعمال کرنا چاہیے؟', 'AI should not replace human teachers but can enhance learning experiences.', 'مصنوعی ذہانت کو انسانی اساتذہ کی جگہ نہیں لینی چاہیے لیکن یہ سیکھنے کے تجربات کو بہتر بنا سکتی ہے۔', 'Technology & Education', 'C1', '2-3 minutes', '30 seconds', 'Introduction → Main Argument → Counter-Argument → Evidence → Conclusion', ARRAY['artificial intelligence', 'education', 'enhancement', 'human interaction', 'personalized learning', 'critical thinking', 'emotional intelligence', 'technological advancement', 'traditional methods', 'digital literacy'], ARRAY['مصنوعی ذہانت', 'تعلیم', 'بہتری', 'انسانی تعامل', 'ذاتی سیکھنا', 'تنقیدی سوچ', 'جذباتی ذہانت', 'ٹیکنالوجی کی ترقی', 'روایتی طریقے', 'ڈیجیٹل خواندگی'], ARRAY['pedagogical', 'algorithmic', 'adaptive', 'comprehensive', 'methodological', 'cognitive', 'interactive', 'innovative', 'systematic', 'analytical'], ARRAY['تعلیمی', 'الگورتھم', 'مطابقت پذیر', 'جامع', 'طریقہ کار', 'ادراکی', 'تعاملی', 'اختراعی', 'منظم', 'تجزیاتی'], 'I believe AI should be integrated into education as a complementary tool rather than a replacement for human teachers. Firstly, AI can provide personalized learning experiences that adapt to individual student needs and learning styles. However, it''s crucial to maintain the human element in education, as teachers offer emotional support, mentorship, and the ability to inspire critical thinking that AI cannot replicate. In contrast, AI excels at processing vast amounts of data and identifying patterns that can help educators make informed decisions about curriculum development and student progress.', 'میں سمجھتا ہوں کہ مصنوعی ذہانت کو انسانی اساتذہ کی جگہ لینے کے بجائے تعلیم میں ایک تکمیلی آلے کے طور پر شامل کرنا چاہیے۔ سب سے پہلے، مصنوعی ذہانت ذاتی سیکھنے کے تجربات فراہم کر سکتی ہے جو انفرادی طالب علم کی ضروریات اور سیکھنے کے انداز کے مطابق ڈھل جاتے ہیں۔ تاہم، تعلیم میں انسانی عنصر کو برقرار رکھنا ضروری ہے، کیونکہ اساتذہ جذباتی مدد، رہنمائی، اور تنقیدی سوچ کو متاثر کرنے کی صلاحیت فراہم کرتے ہیں جو مصنوعی ذہانت نہیں کر سکتی۔ اس کے برعکس، مصنوعی ذہانت بڑی مقدار میں ڈیٹا کو پروسیس کرنے اور ان پیٹرنز کی شناخت کرنے میں ماہر ہے جو تعلیمی کارکنوں کو نصاب کی ترقی اور طالب علم کی پیشرفت کے بارے میں باخبر فیصلے کرنے میں مدد کر سکتے ہیں۔', '{"argument_structure": 25, "critical_thinking": 25, "vocabulary_range": 20, "fluency_grammar": 20, "discourse_markers": 10}', ARRAY['Develop structured argumentation skills', 'Practice critical thinking and analysis', 'Use advanced academic vocabulary', 'Master discourse markers and connectors', 'Express complex ideas with clarity']),
('Is freedom more important than security in today''s world?', 'کیا آج کی دنیا میں آزادی سیکیورٹی سے زیادہ اہم ہے؟', 'Security must be prioritized to protect fundamental freedoms.', 'بنیادی آزادیوں کی حفاظت کے لیے سیکیورٹی کو ترجیح دی جانی چاہیے۔', 'Philosophy & Society', 'C1', '2-3 minutes', '30 seconds', 'Context → Position Statement → Supporting Arguments → Counter-Arguments → Synthesis', ARRAY['freedom', 'security', 'civil liberties', 'surveillance', 'privacy', 'democracy', 'authoritarianism', 'balance', 'rights', 'responsibilities'], ARRAY['آزادی', 'سیکیورٹی', 'شہری آزادیاں', 'نگرانی', 'رازداری', 'جمہوریت', 'آمریت', 'توازن', 'حقوق', 'ذمہ داریاں'], ARRAY['fundamental', 'surveillance', 'authoritarian', 'democratic', 'legitimate', 'arbitrary', 'proportional', 'constitutional', 'sovereign', 'autonomous'], ARRAY['بنیادی', 'نگرانی', 'آمرانہ', 'جمہوری', 'جائز', 'من مانی', 'متناسب', 'آئینی', 'خود مختار', 'خود کار'], 'This is a complex philosophical question that requires careful consideration of both individual rights and collective welfare. While freedom is undoubtedly a fundamental human right, I believe that in today''s interconnected world, security measures are necessary to protect those very freedoms. However, the implementation of security measures must be proportional and transparent to prevent the erosion of civil liberties. The challenge lies in finding the right balance where security enhances rather than restricts our freedoms. Furthermore, we must distinguish between legitimate security concerns and authoritarian overreach that uses security as a pretext for control.', 'یہ ایک پیچیدہ فلسفیانہ سوال ہے جو انفرادی حقوق اور اجتماعی بہبود دونوں کے محتاط جائزے کی ضرورت رکھتا ہے۔ اگرچہ آزادی بلا شبہ ایک بنیادی انسانی حق ہے، لیکن میں سمجھتا ہوں کہ آج کی باہم جڑی ہوئی دنیا میں، انہی آزادیوں کی حفاظت کے لیے سیکیورٹی کے اقدامات ضروری ہیں۔ تاہم، سیکیورٹی کے اقدامات کا نفاذ متناسب اور شفاف ہونا چاہیے تاکہ شہری آزادیوں کے خاتمے کو روکا جا سکے۔ چیلنج یہ ہے کہ صحیح توازن تلاش کیا جائے جہاں سیکیورٹی ہماری آزادیوں کو محدود کرنے کے بجائے انہیں بہتر بنائے۔ مزید برآں، ہمیں جائز سیکیورٹی کے خدشات اور آمرانہ زیادتی کے درمیان فرق کرنا چاہیے جو کنٹرول کے بہانے کے طور پر سیکیورٹی کا استعمال کرتی ہے۔', '{"argument_structure": 25, "critical_thinking": 25, "vocabulary_range": 20, "fluency_grammar": 20, "discourse_markers": 10}', ARRAY['Analyze complex philosophical concepts', 'Present balanced arguments', 'Use sophisticated vocabulary', 'Demonstrate nuanced understanding', 'Express abstract ideas clearly']),
('Does money equal success in modern society?', 'کیا جدید معاشرے میں پیسہ کامیابی کے برابر ہے؟', 'Success encompasses multiple dimensions beyond financial wealth.', 'کامیابی مالی دولت سے آگے کے متعدد پہلوؤں پر محیط ہے۔', 'Philosophy & Economics', 'C1', '2-3 minutes', '30 seconds', 'Definition → Multiple Perspectives → Evidence → Personal View → Conclusion', ARRAY['success', 'wealth', 'happiness', 'fulfillment', 'purpose', 'achievement', 'materialism', 'well-being', 'values', 'priorities'], ARRAY['کامیابی', 'دولت', 'خوشی', 'اطمینان', 'مقصد', 'کامیابی', 'مادیت پسندی', 'بہبود', 'اقدار', 'ترجیحات'], ARRAY['materialistic', 'intrinsic', 'extrinsic', 'fulfillment', 'purpose', 'legacy', 'contribution', 'well-being', 'authentic', 'meaningful'], ARRAY['مادیت پسند', 'داخلی', 'خارجی', 'اطمینان', 'مقصد', 'ورثہ', 'شراکت', 'بہبود', 'اصلی', 'معنی خیز'], 'The equation of money with success represents a reductionist view that fails to capture the multifaceted nature of human achievement and fulfillment. While financial stability is undoubtedly important for meeting basic needs and providing opportunities, true success encompasses various dimensions including personal growth, meaningful relationships, intellectual development, and contribution to society. Furthermore, research consistently shows that beyond a certain threshold, increased wealth does not correlate with increased happiness. Success should be measured by the positive impact one has on others and the fulfillment derived from pursuing one''s passions and values, rather than merely accumulating material possessions.', 'پیسے کو کامیابی کے ساتھ مساوی کرنا ایک تقلیل پسندانہ نظریہ ہے جو انسانی کامیابی اور اطمینان کی کثیر جہتی نوعیت کو پکڑنے میں ناکام ہے۔ اگرچہ مالی استحکام بنیادی ضروریات کو پورا کرنے اور مواقع فراہم کرنے کے لیے بلا شبہ اہم ہے، لیکن حقیقی کامیابی مختلف پہلوؤں پر محیط ہے جن میں ذاتی ترقی، معنی خیز تعلقات، فکری ترقی، اور معاشرے میں شراکت شامل ہیں۔ مزید برآں، تحقیق مسلسل دکھاتی ہے کہ ایک خاص حد سے آگے، بڑھتی ہوئی دولت خوشی میں اضافے سے مطابقت نہیں رکھتی۔ کامیابی کو دوسروں پر مثبت اثر اور اپنے جذبات اور اقدار کی پیروی سے حاصل ہونے والے اطمینان سے ماپا جانا چاہیے، نہ کہ صرف مادی اشیاء جمع کرنے سے۔', '{"argument_structure": 25, "critical_thinking": 25, "vocabulary_range": 20, "fluency_grammar": 20, "discourse_markers": 10}', ARRAY['Challenge conventional wisdom', 'Present evidence-based arguments', 'Use abstract and philosophical vocabulary', 'Demonstrate critical analysis', 'Express nuanced perspectives']),
('Should social media platforms be regulated by governments?', 'کیا سوشل میڈیا پلیٹ فارمز کو حکومتوں کے ذریعے منظم کرنا چاہیے؟', 'Limited regulation is necessary to protect users while preserving innovation.', 'صارفین کی حفاظت کے لیے محدود ضابطہ کاری ضروری ہے جبکہ اختراع کو برقرار رکھا جائے۔', 'Technology & Governance', 'C1', '2-3 minutes', '30 seconds', 'Problem Statement → Stakeholder Analysis → Regulatory Options → Recommendations → Implementation', ARRAY['regulation', 'social media', 'privacy', 'misinformation', 'innovation', 'democracy', 'censorship', 'transparency', 'accountability', 'freedom of expression'], ARRAY['ضابطہ کاری', 'سوشل میڈیا', 'رازداری', 'غلط معلومات', 'اختراع', 'جمہوریت', 'سینسرشپ', 'شفافیت', 'جوابدہی', 'اظہار رائے کی آزادی'], ARRAY['algorithmic', 'disinformation', 'misinformation', 'transparency', 'accountability', 'censorship', 'moderation', 'compliance', 'oversight', 'stakeholder'], ARRAY['الگورتھم', 'غلط معلومات', 'غلط معلومات', 'شفافیت', 'جوابدہی', 'سینسرشپ', 'اعتدال', 'تعمیل', 'نگرانی', 'حصہ دار'], 'The regulation of social media platforms presents a complex challenge that requires balancing multiple competing interests. On one hand, these platforms have become essential public spaces for discourse, necessitating protection of free expression and innovation. On the other hand, the spread of misinformation, privacy violations, and algorithmic manipulation require some form of oversight. I believe that targeted regulation focusing on transparency, accountability, and user protection is necessary, while avoiding overly restrictive measures that could stifle innovation or enable government censorship. The key is implementing regulations that address specific harms without compromising the fundamental benefits these platforms provide to democratic discourse.', 'سوشل میڈیا پلیٹ فارمز کی ضابطہ کاری ایک پیچیدہ چیلنج پیش کرتی ہے جو متعدد مقابلہ جاتی مفادات کے توازن کی ضرورت رکھتی ہے۔ ایک طرف، یہ پلیٹ فارمز گفتگو کے لیے ضروری عوامی جگہیں بن گئے ہیں، جس کے لیے آزاد اظہار اور اختراع کی حفاظت ضروری ہے۔ دوسری طرف، غلط معلومات کا پھیلاؤ، رازداری کی خلاف ورزی، اور الگورتھم کا استحصال کسی نہ کسی شکل میں نگرانی کی ضرورت رکھتے ہیں۔ میں سمجھتا ہوں کہ شفافیت، جوابدہی، اور صارف کی حفاظت پر مرکوز ہدف شدہ ضابطہ کاری ضروری ہے، جبکہ زیادہ محدود اقدامات سے بچنا چاہیے جو اختراع کو روک سکتے ہیں یا حکومتی سینسرشپ کو ممکن بنا سکتے ہیں۔ کلید یہ ہے کہ ایسے ضوابط نافذ کیے جائیں جو مخصوص نقصانات کو حل کریں بغیر ان بنیادی فوائد سے سمجھوتہ کیے جو یہ پلیٹ فارم جمہوری گفتگو کو فراہم کرتے ہیں۔', '{"argument_structure": 25, "critical_thinking": 25, "vocabulary_range": 20, "fluency_grammar": 20, "discourse_markers": 10}', ARRAY['Analyze complex policy issues', 'Present balanced regulatory perspectives', 'Use technical and policy vocabulary', 'Demonstrate nuanced understanding', 'Express sophisticated arguments']),
('Is the traditional university education model still relevant?', 'کیا روایتی یونیورسٹی تعلیم کا ماڈل اب بھی متعلقہ ہے؟', 'The traditional model needs significant adaptation to remain relevant in the digital age.', 'ڈیجیٹل دور میں متعلقہ رہنے کے لیے روایتی ماڈل کو اہم مطابقت کی ضرورت ہے۔', 'Education & Technology', 'C1', '2-3 minutes', '30 seconds', 'Historical Context → Current Challenges → Adaptation Strategies → Future Vision → Recommendations', ARRAY['university', 'education', 'digital transformation', 'online learning', 'traditional methods', 'innovation', 'accessibility', 'cost-effectiveness', 'quality', 'adaptation'], ARRAY['یونیورسٹی', 'تعلیم', 'ڈیجیٹل تبدیلی', 'آن لائن سیکھنا', 'روایتی طریقے', 'اختراع', 'دستیابی', 'لاگت کی تاثیر', 'معیار', 'مطابقت'], ARRAY['pedagogical', 'methodological', 'transformative', 'disruptive', 'hybrid', 'blended', 'interactive', 'collaborative', 'experiential', 'adaptive'], ARRAY['تعلیمی', 'طریقہ کار', 'تبدیلی', 'خلل انداز', 'مخلوط', 'ملایا ہوا', 'تعاملی', 'تعاونی', 'تجرباتی', 'مطابقت پذیر'], 'The traditional university model, while historically valuable, requires substantial evolution to meet the demands of the 21st century. While the core elements of critical thinking, research skills, and intellectual discourse remain essential, the delivery methods and accessibility need significant transformation. The rise of digital technologies, changing job market demands, and increasing costs necessitate a hybrid approach that combines the best of traditional pedagogy with innovative digital tools. However, we must be careful not to lose the invaluable aspects of face-to-face interaction, mentorship, and the development of social and emotional intelligence that traditional universities uniquely provide.', 'روایتی یونیورسٹی ماڈل، اگرچہ تاریخی طور پر قیمتی ہے، کو 21ویں صدی کی ضروریات کو پورا کرنے کے لیے اہم ارتقاء کی ضرورت ہے۔ اگرچہ تنقیدی سوچ، تحقیق کی مہارتیں، اور فکری گفتگو کے بنیادی عناصر ضروری رہتے ہیں، لیکن ترسیل کے طریقے اور دستیابی کو اہم تبدیلی کی ضرورت ہے۔ ڈیجیٹل ٹیکنالوجیز کا عروج، تبدیل ہوتی ہوئی ملازمت کی مارکیٹ کی ضرورت، اور بڑھتی ہوئی لاگت ایک مخلوط طریقہ کار کی ضرورت رکھتے ہیں جو روایتی تعلیم کے بہترین پہلوؤں کو اختراعی ڈیجیٹل اوزاروں کے ساتھ جوڑتا ہے۔ تاہم، ہمیں احتیاط کرنی چاہیے کہ روایتی یونیورسٹیوں کی منفرد فراہم کردہ آمنے سامنے تعامل، رہنمائی، اور سماجی اور جذباتی ذہانت کی ترقی کے انمول پہلوؤں کو نہ کھو دیں۔', '{"argument_structure": 25, "critical_thinking": 25, "vocabulary_range": 20, "fluency_grammar": 20, "discourse_markers": 10}', ARRAY['Analyze institutional change', 'Present balanced perspectives on tradition vs innovation', 'Use academic and technical vocabulary', 'Demonstrate forward-thinking analysis', 'Express complex educational concepts']);

-- =============================================================================
-- STAGE 5 EXERCISE 2: ACADEMIC PRESENTATION & ANALYSIS
-- =============================================================================

-- Table for Academic Presentation & Analysis
CREATE TABLE IF NOT EXISTS public.ai_tutor_stage5_exercise2_academic_presentation (
    id SERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    topic_urdu TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'C1',
    speaking_duration TEXT NOT NULL,
    thinking_time TEXT NOT NULL,
    expected_structure TEXT NOT NULL,
    expected_keywords TEXT[] NOT NULL,
    expected_keywords_urdu TEXT[] NOT NULL,
    vocabulary_focus TEXT[] NOT NULL,
    vocabulary_focus_urdu TEXT[] NOT NULL,
    model_response TEXT NOT NULL,
    model_response_urdu TEXT NOT NULL,
    evaluation_criteria JSONB NOT NULL,
    learning_objectives TEXT[] NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert data for Academic Presentation & Analysis
INSERT INTO public.ai_tutor_stage5_exercise2_academic_presentation (topic, topic_urdu, category, difficulty, speaking_duration, thinking_time, expected_structure, expected_keywords, expected_keywords_urdu, vocabulary_focus, vocabulary_focus_urdu, model_response, model_response_urdu, evaluation_criteria, learning_objectives) VALUES
('The impact of climate change on future generations', 'موسمیاتی تبدیلی کا مستقبل کی نسلوں پر اثر', 'Environmental Science', 'C1', '3 minutes', '30 seconds', 'Introduction → Thesis Statement → Supporting Evidence → Counter-Arguments → Conclusion', ARRAY['climate change', 'future generations', 'environmental impact', 'sustainability', 'carbon emissions', 'renewable energy', 'policy changes', 'global warming', 'ecosystem', 'intergenerational equity'], ARRAY['موسمیاتی تبدیلی', 'مستقبل کی نسلیں', 'ماحولیاتی اثر', 'پائیداری', 'کاربن اخراج', 'قابل تجدید توانائی', 'پالیسی تبدیلیاں', 'عالمی گرمی', 'ماحولیاتی نظام', 'نسلی انصاف'], ARRAY['catastrophic', 'irreversible', 'mitigation', 'adaptation', 'anthropogenic', 'biodiversity', 'resilience', 'sustainable development', 'carbon footprint', 'greenhouse gases'], ARRAY['تباہ کن', 'ناقابل واپسی', 'کمی', 'مطابقت', 'انسانی وجہ سے', 'حیاتیاتی تنوع', 'مزاحمت', 'پائیدار ترقی', 'کاربن فٹ پرنٹ', 'گرین ہاؤس گیسز'], 'Climate change represents one of the most pressing challenges facing future generations. The scientific consensus is clear: human activities are driving unprecedented global warming, with potentially catastrophic consequences. Rising sea levels threaten coastal communities, extreme weather events are becoming more frequent, and biodiversity loss accelerates at alarming rates. However, we must acknowledge that the burden of climate change will fall disproportionately on future generations who had no role in creating this crisis. The concept of intergenerational equity demands that we take immediate action. Transitioning to renewable energy sources, implementing carbon pricing mechanisms, and investing in sustainable infrastructure are not merely policy choices but moral imperatives. While some argue that such measures are economically costly, the long-term costs of inaction far exceed the investments required for mitigation. Future generations deserve a habitable planet, and we have both the responsibility and the capability to ensure they inherit one.', 'موسمیاتی تبدیلی مستقبل کی نسلوں کے سامنے آنے والے سب سے اہم چیلنجز میں سے ایک ہے۔ سائنسی اتفاق رائے واضح ہے: انسانی سرگرمیاں بے مثال عالمی گرمی کو جنم دے رہی ہیں، جس کے ممکنہ طور پر تباہ کن نتائج ہیں۔ بڑھتی ہوئی سمندری سطحیں ساحلی برادریوں کو خطرے میں ڈال رہی ہیں، شدید موسمی واقعات زیادہ کثرت سے ہو رہے ہیں، اور حیاتیاتی تنوع کی کمی خطرناک شرح سے بڑھ رہی ہے۔ تاہم، ہمیں تسلیم کرنا چاہیے کہ موسمیاتی تبدیلی کا بوجھ مستقبل کی نسلوں پر غیر متناسب طور پر پڑے گا جن کا اس بحران کو پیدا کرنے میں کوئی کردار نہیں تھا۔ نسلی انصاف کا تصور مطالبہ کرتا ہے کہ ہم فوری کارروائی کریں۔ قابل تجدید توانائی کے ذرائع کی طرف منتقلی، کاربن قیمتوں کے میکانزم کو نافذ کرنا، اور پائیدار بنیادی ڈھانچے میں سرمایہ کاری صرف پالیسی کے انتخاب نہیں بلکہ اخلاقی ضرورتیں ہیں۔ جبکہ کچھ لوگ دلیل دیتے ہیں کہ ایسی تدابیر معاشی طور پر مہنگی ہیں، عدم کارروائی کی طویل مدتی لاگت کمی کے لیے درکار سرمایہ کاری سے کہیں زیادہ ہے۔ مستقبل کی نسلوں کو ایک قابل رہائش سیارہ ملنا چاہیے، اور ہمارے پاس یہ یقینی بنانے کی ذمہ داری اور صلاحیت دونوں ہیں کہ وہ ایک وراثت میں پائیں۔', '{"argument_structure": 25, "evidence_usage": 25, "academic_tone": 20, "fluency_pacing": 15, "vocabulary_range": 15}', ARRAY['Develop structured academic argumentation skills', 'Use evidence and statistics effectively in presentations', 'Master formal academic tone and vocabulary', 'Practice time-bound logical structuring', 'Build confidence in delivering extended academic speeches']);

-- =============================================================================
-- STAGE 5 EXERCISE 3: PROFESSIONAL INTERVIEW MASTERY
-- =============================================================================

-- Table for Professional Interview Mastery
CREATE TABLE IF NOT EXISTS public.ai_tutor_stage5_exercise3_interview_mastery (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    category TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'C1',
    question_type TEXT NOT NULL,
    expected_structure TEXT NOT NULL,
    expected_keywords TEXT[] NOT NULL,
    vocabulary_focus TEXT[] NOT NULL,
    model_answer TEXT NOT NULL,
    evaluation_criteria JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert data for Professional Interview Mastery
INSERT INTO public.ai_tutor_stage5_exercise3_interview_mastery (question, category, difficulty, question_type, expected_structure, expected_keywords, vocabulary_focus, model_answer, evaluation_criteria) VALUES
('Can you describe a professional challenge you overcame and what you learned from it?', 'Professional Experience', 'C1', 'Reflective', 'Situation → Challenge → Action → Result → Learning', ARRAY['challenge', 'problem', 'solution', 'learning', 'outcome', 'experience', 'growth', 'development', 'overcome', 'achievement'], ARRAY['adversity', 'resilience', 'perseverance', 'breakthrough', 'transformation', 'insight', 'adaptability', 'innovation', 'collaboration', 'leadership'], 'I faced a significant challenge when our team was tasked with implementing a new software system within a tight three-month deadline. The main obstacle was resistance from senior staff who were comfortable with the old system. I took a collaborative approach by organizing training sessions, creating user-friendly documentation, and addressing concerns individually. The breakthrough came when I identified a key stakeholder who became an advocate for the change. Through this experience, I learned the importance of change management, effective communication, and building consensus. The project was completed successfully, and the team''s productivity increased by 25%. This taught me that challenges often present opportunities for growth and that persistence combined with empathy can overcome even the most difficult obstacles.', '{"relevance_structure": 25, "reflective_vocabulary": 25, "soft_skills": 25, "strategic_thinking": 25}'),
('What motivates you to keep learning and growing professionally?', 'Personal Motivation', 'C1', 'Motivational', 'Core Values → Personal Goals → Professional Aspirations → Continuous Improvement', ARRAY['motivation', 'goals', 'growth', 'curiosity', 'future', 'passion', 'development', 'excellence', 'innovation', 'impact'], ARRAY['intrinsic motivation', 'intellectual curiosity', 'professional development', 'continuous learning', 'skill enhancement', 'knowledge acquisition', 'career advancement', 'personal fulfillment', 'expertise', 'mastery'], 'My motivation stems from a deep-seated belief that knowledge is the foundation of meaningful contribution. I''m driven by intellectual curiosity and the desire to solve complex problems that can make a real difference. The rapid pace of technological advancement means that staying current isn''t just beneficial—it''s essential. I find immense satisfaction in mastering new skills and applying them to create innovative solutions. My professional growth is fueled by the understanding that expertise is not a destination but a continuous journey. I''m particularly motivated by the opportunity to mentor others and contribute to their development, as this creates a multiplier effect on impact. The prospect of being at the forefront of industry developments and helping shape the future of my field is incredibly energizing. Ultimately, my motivation comes from the belief that continuous learning enables me to be more effective, more creative, and more valuable to both my organization and society at large.', '{"relevance_structure": 25, "reflective_vocabulary": 25, "soft_skills": 25, "strategic_thinking": 25}');

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Indexes for Advanced Debate & Argumentation
CREATE INDEX IF NOT EXISTS idx_advanced_debate_category ON public.ai_tutor_stage5_exercise1_advanced_debate(category);
CREATE INDEX IF NOT EXISTS idx_advanced_debate_difficulty ON public.ai_tutor_stage5_exercise1_advanced_debate(difficulty);
CREATE INDEX IF NOT EXISTS idx_advanced_debate_topic ON public.ai_tutor_stage5_exercise1_advanced_debate(topic);

-- Indexes for Academic Presentation & Analysis
CREATE INDEX IF NOT EXISTS idx_academic_presentation_category ON public.ai_tutor_stage5_exercise2_academic_presentation(category);
CREATE INDEX IF NOT EXISTS idx_academic_presentation_difficulty ON public.ai_tutor_stage5_exercise2_academic_presentation(difficulty);
CREATE INDEX IF NOT EXISTS idx_academic_presentation_topic ON public.ai_tutor_stage5_exercise2_academic_presentation(topic);

-- Indexes for Professional Interview Mastery
CREATE INDEX IF NOT EXISTS idx_interview_mastery_category ON public.ai_tutor_stage5_exercise3_interview_mastery(category);
CREATE INDEX IF NOT EXISTS idx_interview_mastery_difficulty ON public.ai_tutor_stage5_exercise3_interview_mastery(difficulty);
CREATE INDEX IF NOT EXISTS idx_interview_mastery_question_type ON public.ai_tutor_stage5_exercise3_interview_mastery(question_type);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE public.ai_tutor_stage5_exercise1_advanced_debate ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_tutor_stage5_exercise2_academic_presentation ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_tutor_stage5_exercise3_interview_mastery ENABLE ROW LEVEL SECURITY;

-- RLS Policies for public access (these are content tables, not user-specific)
CREATE POLICY "Anyone can view advanced debate topics" ON public.ai_tutor_stage5_exercise1_advanced_debate FOR SELECT USING (true);
CREATE POLICY "Anyone can view academic presentation topics" ON public.ai_tutor_stage5_exercise2_academic_presentation FOR SELECT USING (true);
CREATE POLICY "Anyone can view interview mastery questions" ON public.ai_tutor_stage5_exercise3_interview_mastery FOR SELECT USING (true);

-- =============================================================================
-- GRANT PERMISSIONS
-- =============================================================================

-- Grant permissions for all tables
GRANT ALL ON public.ai_tutor_stage5_exercise1_advanced_debate TO anon, authenticated;
GRANT ALL ON public.ai_tutor_stage5_exercise2_academic_presentation TO anon, authenticated;
GRANT ALL ON public.ai_tutor_stage5_exercise3_interview_mastery TO anon, authenticated;

-- Grant permissions for sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Verify data insertion
SELECT 'Advanced Debate & Argumentation' as table_name, COUNT(*) as record_count FROM public.ai_tutor_stage5_exercise1_advanced_debate
UNION ALL
SELECT 'Academic Presentation & Analysis' as table_name, COUNT(*) as record_count FROM public.ai_tutor_stage5_exercise2_academic_presentation
UNION ALL
SELECT 'Professional Interview Mastery' as table_name, COUNT(*) as record_count FROM public.ai_tutor_stage5_exercise3_interview_mastery;

-- Sample data verification
SELECT 'Sample Advanced Debate & Argumentation:' as info;
SELECT id, topic, topic_urdu, category FROM public.ai_tutor_stage5_exercise1_advanced_debate LIMIT 3;

SELECT 'Sample Academic Presentation & Analysis:' as info;
SELECT id, topic, topic_urdu, category FROM public.ai_tutor_stage5_exercise2_academic_presentation LIMIT 3;

SELECT 'Sample Professional Interview Mastery:' as info;
SELECT id, question, category, question_type FROM public.ai_tutor_stage5_exercise3_interview_mastery LIMIT 3;
