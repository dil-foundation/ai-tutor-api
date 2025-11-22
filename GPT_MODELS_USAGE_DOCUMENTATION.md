# GPT Models Usage Documentation

## Overview
This document provides a comprehensive list of all OpenAI GPT models used in the AI Tutor Backend, along with the functions that utilize each model and their specific purposes.

---

## GPT Models Used

### 1. **gpt-4o-mini** (formerly gpt-4)
A cost-effective language model used for various evaluation and assessment tasks. Replaced gpt-4 to minimize costs.

### 2. **gpt-4-turbo**
An optimized version of GPT-4 with improved performance and speed, used for translation and proficiency assessment.

### 3. **gpt-4o**
The latest optimized GPT-4 model, used extensively throughout the application for feedback generation, evaluation, and conversation analysis.

### 4. **gpt-4o-realtime-preview-2025-06-03**
A specialized real-time model for audio-to-audio conversations, used for live voice interactions.

---

## Detailed Model Usage by Function

### **gpt-4o-mini** Model (Cost-Optimized)

#### 1. `evaluate_cefr_level()` - `app/services/cefr_evaluator.py`
- **Purpose**: Evaluates English writing samples and classifies them into CEFR levels (A0, A1, A2, B1, B2, C1, C2)
- **Function**: `evaluate_cefr_level(writing_sample: str) -> str`
- **Temperature**: 0.3
- **Usage**: CEFR level assessment for initial user placement

#### 2. `evaluate_dialogue_with_gpt()` - `app/services/dialogue_evaluator.py`
- **Purpose**: Evaluates student's spoken response in English conversation practice
- **Function**: `evaluate_dialogue_with_gpt(ai_prompt: str, expected_keywords: str, user_response: str) -> dict`
- **Temperature**: 0.7
- **Returns**: JSON with feedback, grammar_score, fluency_score, relevance_score, keyword_score, and overall score
- **Usage**: Functional dialogue evaluation

#### 3. `evaluate_response()` - `app/services/evaluator.py`
- **Purpose**: Evaluates student's spoken response based on grammar, fluency, relevance, and overall score
- **Function**: `evaluate_response(question: str, expected_answer: str, user_response: str) -> dict`
- **Temperature**: 0.7
- **Returns**: JSON with feedback, grammar_score, fluency_score, relevance_score, and overall score
- **Usage**: General response evaluation

#### 4. `generate_feedback()` - `app/services/feedback_stage_2.py`
- **Purpose**: Evaluates user's spoken English narration for relevance, keyword use, and fluency
- **Function**: `generate_feedback(transcript: str, example: str, keywords: list[str]) -> dict`
- **Temperature**: 0.5
- **Returns**: Score (float) and feedback (str)
- **Usage**: Stage 2 feedback generation

#### 5. `extract_quiz_from_text_using_gpt()` - `app/services/gpt_parser.py`
- **Purpose**: Extracts quiz questions from educational text using GPT
- **Function**: `extract_quiz_from_text_using_gpt(text: str) -> Dict`
- **Temperature**: 0.7
- **Returns**: JSON with quiz title and questions array
- **Usage**: PDF quiz extraction and parsing

#### 6. `evaluate_response_ex1_stage3()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 3 Exercise 1 (Narrative Storytelling) responses
- **Function**: `evaluate_response_ex1_stage3(expected_keywords: list, user_response: str, prompt: str, prompt_urdu: str, model_answer: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 1000
- **Usage**: Comprehensive feedback on narrative structure, past tense usage, and fluency

#### 7. `evaluate_response_ex1_stage6()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 6 Exercise 1 (AI-Guided Spontaneous Speech) responses
- **Function**: `evaluate_response_ex1_stage6(expected_keywords, user_text, topic_text, model_response, evaluation_criteria)`
- **Temperature**: 0.3
- **Max Tokens**: 1500
- **Usage**: C2-level spontaneous speech evaluation

#### 8. `evaluate_response_ex2_stage6()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 6 Exercise 2 (Roleplay - Handle a Sensitive Scenario) responses
- **Function**: `evaluate_response_ex2_stage6(expected_keywords, user_text, scenario_text, model_response, evaluation_criteria)`
- **Temperature**: 0.3
- **Max Tokens**: 1500
- **Usage**: C2-level sensitive scenario roleplay evaluation

---

### **gpt-4-turbo** Model

#### 1. `translate_urdu_to_english()` - `app/services/translation.py`
- **Purpose**: Translates Urdu, Hindi, or other languages to natural, fluent, grammatically correct English
- **Function**: `translate_urdu_to_english(text: str) -> str`
- **Usage**: Language translation service

#### 2. `translate_to_urdu()` - `app/services/translation.py`
- **Purpose**: Translates English or other languages to accurate Pakistani Urdu script
- **Function**: `translate_to_urdu(text: str) -> str`
- **Usage**: Reverse translation to Urdu

#### 3. `assess_english_proficiency()` - `app/services/proficiency_assessment.py`
- **Purpose**: Assesses user's actual English proficiency level based on written text and assigns starting stage (0-6)
- **Function**: `async def assess_english_proficiency(text: str) -> int`
- **Temperature**: 0.2
- **Max Tokens**: 50
- **Response Format**: JSON object
- **Usage**: Initial proficiency assessment during user sign-up

---

### **gpt-4o** Model

#### 1. `_execute_ai_analysis()` - `app/services/feedback.py`
- **Purpose**: Core function for English-only conversation analysis with dynamic AI settings
- **Function**: `_execute_ai_analysis(prompt: str, stage_name: str) -> dict`
- **Temperature**: 0.7
- **Response Format**: JSON object
- **Usage**: Main AI analysis engine for English-only mode with configurable behavior

#### 2. `get_fluency_feedback_eng()` - `app/services/feedback.py`
- **Purpose**: Evaluates spoken English against expected sentence (English-only feedback)
- **Function**: `get_fluency_feedback_eng(user_text: str, expected_text: str) -> dict`
- **Temperature**: 0.7
- **Returns**: Pronunciation score, tone & intonation, and feedback
- **Usage**: English-only fluency evaluation

#### 3. `get_fluency_feedback()` - `app/services/feedback.py`
- **Purpose**: Evaluates spoken English against expected sentence with Urdu feedback
- **Function**: `get_fluency_feedback(user_text: str, expected_text: str) -> dict`
- **Temperature**: 0.7
- **Returns**: Pronunciation score, tone & intonation (Urdu), and feedback (Urdu)
- **Usage**: Bilingual fluency evaluation

#### 4. `evaluate_response_eng()` - `app/services/feedback.py`
- **Purpose**: Evaluates response for English-only mode
- **Function**: `evaluate_response_eng(expected: str, actual: str) -> dict`
- **Temperature**: 0.7
- **Usage**: English-only response evaluation

#### 5. `evaluate_response_ex1_stage1()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 1 Exercise 1 responses
- **Function**: `evaluate_response_ex1_stage1(expected_phrase: str, user_response: str) -> dict`
- **Temperature**: 0.7
- **Usage**: Basic phrase repetition evaluation

#### 6. `evaluate_response_ex2_stage1()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 1 Exercise 2 responses
- **Function**: `evaluate_response_ex2_stage1(expected_answers: list, user_response: str) -> dict`
- **Temperature**: 0.7
- **Usage**: Multiple choice answer evaluation

#### 7. `evaluate_response_ex3_stage1()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 1 Exercise 3 responses
- **Function**: `evaluate_response_ex3_stage1(expected_keywords: list, user_response: str, ai_prompt: str) -> dict`
- **Temperature**: 0.7
- **Usage**: Keyword-based response evaluation

#### 8. `evaluate_response_ex1_stage2()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 2 Exercise 1 responses
- **Function**: `evaluate_response_ex1_stage2(expected_keywords: list, user_response: str, phrase: str, example: str) -> dict`
- **Temperature**: 0.7
- **Usage**: Daily routine narration evaluation

#### 9. `evaluate_response_ex2_stage2()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 2 Exercise 2 responses
- **Function**: `evaluate_response_ex2_stage2(expected_answers: list, user_response: str, question: str, question_urdu: str) -> dict`
- **Temperature**: 0.7
- **Usage**: Question-answer evaluation

#### 10. `evaluate_response_ex3_stage2()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 2 Exercise 3 (Roleplay Simulation) responses
- **Function**: `evaluate_response_ex3_stage2(conversation_history: list, scenario_context: str, expected_keywords: list, ai_character: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 2000
- **Usage**: Roleplay conversation quality analysis

#### 11. `evaluate_response_ex2_stage3()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 3 Exercise 2 (Group Dialogue) responses
- **Function**: `evaluate_response_ex2_stage3(expected_responses: list, user_response: str, context: str, initial_prompt: str, follow_up_turns: list) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 1000
- **Usage**: Group dialogue evaluation with agreement/disagreement expressions

#### 12. `evaluate_response_ex3_stage3()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 3 Exercise 3 (Problem-Solving Simulations) responses
- **Function**: `evaluate_response_ex3_stage3(expected_keywords: list, user_response: str, problem_description: str, context: str, polite_phrases: list, sample_responses: list) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 1000
- **Usage**: Problem-solving scenario evaluation

#### 13. `evaluate_response_ex1_stage4()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 4 Exercise 1 (Abstract Topic Monologue) responses
- **Function**: `evaluate_response_ex1_stage4(user_response: str, topic: str, key_connectors: list, vocabulary_focus: list, model_response: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 1500
- **Usage**: B2-level abstract topic monologue evaluation

#### 14. `evaluate_response_ex2_stage4()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 4 Exercise 2 (Mock Interview Practice) responses
- **Function**: `evaluate_response_ex2_stage4(user_response: str, question: str, expected_keywords: list, vocabulary_focus: list, model_response: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 1500
- **Usage**: Mock interview response evaluation

#### 15. `evaluate_response_ex3_stage4()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 4 Exercise 3 (News Analysis & Discussion) responses
- **Function**: `evaluate_response_ex3_stage4(user_response: str, news_title: str, summary_text: str, expected_keywords: list, vocabulary_focus: list, model_summary: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 1500
- **Usage**: News analysis and discussion evaluation

#### 16. `evaluate_response_ex1_stage5()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 5 Exercise 1 (Debate & Argumentation) responses
- **Function**: `evaluate_response_ex1_stage5(user_response: str, topic: str, ai_position: str, expected_keywords: list, vocabulary_focus: list, model_response: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 2000
- **Usage**: C1-level debate and argumentation evaluation

#### 17. `evaluate_response_ex2_stage5()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 5 Exercise 2 (Academic Presentation) responses
- **Function**: `evaluate_response_ex2_stage5(user_response: str, topic: str, expected_keywords: list, vocabulary_focus: list, model_response: str, expected_structure: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 2000
- **Usage**: Academic presentation evaluation

#### 18. `evaluate_response_ex3_stage5()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 5 Exercise 3 (Complex Question Analysis) responses
- **Function**: `evaluate_response_ex3_stage5(user_response: str, question: str, expected_keywords: list, vocabulary_focus: list, model_answer: str, expected_structure: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 2000
- **Usage**: Complex question analysis evaluation

#### 19. `evaluate_response_ex3_stage6()` - `app/services/feedback.py`
- **Purpose**: Evaluates Stage 6 Exercise 3 (Critical Opinion Builder) responses
- **Function**: `evaluate_response_ex3_stage6(user_response: str, topic: str, expected_keywords: list, vocabulary_focus: list, academic_expressions: list, model_response: str, expected_structure: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 1500
- **Usage**: C2-level critical opinion building evaluation

#### 20. `correct_english_text()` - `app/services/english_correction.py`
- **Purpose**: Corrects English text for grammar, syntax, and naturalness
- **Function**: `correct_english_text(text: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 500
- **Returns**: JSON with has_grammar_issues, corrected_text, feedback, issues, and confidence
- **Usage**: Grammar and syntax correction

#### 21. `detect_accent_issues()` - `app/services/english_correction.py`
- **Purpose**: Detects thick accent patterns and provides pronunciation guidance
- **Function**: `detect_accent_issues(text: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 500
- **Returns**: JSON with has_accent_issues, accent_patterns, feedback, pronunciation_tips, and confidence
- **Usage**: Accent pattern detection for Urdu/Hindi speakers

#### 22. `get_pronunciation_guide()` - `app/services/english_correction.py`
- **Purpose**: Provides pronunciation guide for specific words
- **Function**: `get_pronunciation_guide(word: str) -> dict`
- **Temperature**: 0.3
- **Max Tokens**: 300
- **Returns**: JSON with word, phonetic, common_mistakes, tips, and audio_cues
- **Usage**: Word-specific pronunciation assistance

#### 23. `_generate_ai_response()` - `app/services/roleplay_agent.py`
- **Purpose**: Generates AI response for roleplay scenarios
- **Function**: `_generate_ai_response(session_data: Dict, user_input: str, scenario: Dict) -> str`
- **Temperature**: 0.7
- **Max Tokens**: 150
- **Usage**: Roleplay conversation generation

---

### **gpt-4o-realtime-preview-2025-06-03** Model

#### 1. `talk_to_openai()` - `app/routes/conversation_ws_2.py`
- **Purpose**: Connects to OpenAI's Realtime API for audio-to-audio conversations
- **Function**: `async def talk_to_openai(audio_bytes: bytes) -> bytes`
- **Model**: `gpt-4o-realtime-preview-2025-06-03`
- **Modalities**: Audio and text
- **Input Format**: PCM16
- **Output Format**: PCM16
- **Sample Rate**: 24kHz
- **Usage**: Real-time voice conversation with English tutor for Urdu-speaking learners
- **WebSocket Endpoint**: `/ws/learn_gpt`

---

## Summary Statistics

### Model Usage Count:
- **gpt-4o-mini** (replaced gpt-4 for cost optimization): 15 functions (Stage 1-4, core functions)
- **gpt-4-turbo**: 3 functions
- **gpt-4o**: 14 functions (Stage 5-6 advanced evaluations + other critical functions)
- **gpt-4o-realtime-preview-2025-06-03**: 1 function

### Total Functions Using GPT Models: **33**

### Model Selection Strategy:
- **gpt-4o-mini**: Used for Stage 1-4 evaluations and basic functions (cost-effective)
- **gpt-4o**: Used for Stage 5-6 (C1/C2 Advanced) evaluations requiring sophisticated analysis

---

## File Locations

### Service Files:
- `app/services/feedback.py` - Main feedback and evaluation service (18 functions)
- `app/services/translation.py` - Translation services (2 functions)
- `app/services/cefr_evaluator.py` - CEFR level evaluation (1 function)
- `app/services/proficiency_assessment.py` - Proficiency assessment (1 function)
- `app/services/english_correction.py` - English correction and accent detection (3 functions)
- `app/services/dialogue_evaluator.py` - Dialogue evaluation (1 function)
- `app/services/evaluator.py` - General response evaluation (1 function)
- `app/services/feedback_stage_2.py` - Stage 2 feedback (1 function)
- `app/services/gpt_parser.py` - Quiz extraction (1 function)
- `app/services/roleplay_agent.py` - Roleplay agent (1 function)

### Route Files:
- `app/routes/conversation_ws_2.py` - Real-time audio conversation (1 function)
- `app/routes/gpt_quiz_parser.py` - Quiz parser routes (uses gpt_parser service)

---

## Configuration

All GPT models are configured using the `OPENAI_API_KEY` environment variable, which is loaded from:
- `app/config.py` - Central configuration file
- Environment variables (via `os.getenv()`)

---

## Notes

1. **Temperature Settings**: Most evaluation functions use temperature 0.3 for consistent, focused responses, while conversational functions use 0.7 for more natural variation.

2. **Response Formats**: Many functions use `response_format={"type": "json_object"}` to ensure structured JSON responses.

3. **Token Limits**: Token limits vary by function complexity:
   - Simple evaluations: 300-500 tokens
   - Standard evaluations: 1000-1500 tokens
   - Complex evaluations: 2000 tokens

4. **Error Handling**: All functions include comprehensive error handling with fallback responses.

5. **Real-time API**: The real-time API uses WebSocket connections for low-latency audio streaming.

---

## Last Updated
Generated on: 2025-01-27

