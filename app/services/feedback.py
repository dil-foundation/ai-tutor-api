from openai import OpenAI
from app.config import OPENAI_API_KEY
import json
import re
import asyncio
from app.services.settings_manager import get_ai_settings
from app.schemas.settings import AISettings
from app.services.safety_manager import get_ai_safety_settings
from app.schemas.safety import AISafetyEthicsSettings
from typing import Optional

# Global variable to hold the event loop passed from the main thread
main_thread_loop = None

client = OpenAI(api_key=OPENAI_API_KEY)


# --- Dynamic System Prompt Builder for AI Tutor Settings ---

def _build_system_prompt_from_settings(base_prompt: str, settings: AISettings) -> str:
    """
    Constructs a dynamic system prompt by augmenting a base prompt with AI settings.
    This function ensures that the AI's behavior aligns with the configuration
    set by the administrator in the AI Tutor Settings.
    """
    prompt_parts = [base_prompt]

    # Append settings-based instructions to the prompt
    prompt_parts.append("\n--- AI Behavior Guidelines ---")
    prompt_parts.append(f"Your personality must be: {settings.personality_type}.")
    prompt_parts.append(f"Adopt a {settings.response_style} response style.")
    prompt_parts.append(f"When correcting errors, your style should be {settings.error_correction_style}.")

    if settings.cultural_sensitivity:
        prompt_parts.append("Always ensure your responses are culturally sensitive and universally appropriate.")
    if settings.age_appropriate:
        prompt_parts.append("Ensure your language and topics are age-appropriate for all learners.")
    if settings.professional_context:
        prompt_parts.append("Maintain a professional context in all your examples and conversational topics.")
    
    if settings.custom_prompts and settings.custom_prompts.strip():
        prompt_parts.append(f"\n**CRITICAL CUSTOM INSTRUCTIONS:**\n{settings.custom_prompts}")

    return "\n".join(prompt_parts)

def _apply_safety_guidelines(prompt: str, safety_settings: AISafetyEthicsSettings) -> str:
    """
    Applies a layer of safety and ethics rules to an existing system prompt.
    This ensures all AI responses adhere to the configured safety standards.
    """
    prompt_parts = [prompt]
    prompt_parts.append("\n--- AI Safety & Ethics Mandates (Strictly Enforced) ---")
    if safety_settings.harmful_content_prevention:
        prompt_parts.append("- You must strictly avoid generating harmful, unethical, racist, sexist, toxic, dangerous, or illegal content.")
    if safety_settings.toxicity_detection:
        prompt_parts.append("- You must not use or promote toxic language or behavior.")
    if safety_settings.bias_detection:
        prompt_parts.append("- You must remain neutral and avoid any form of political, social, or personal bias.")
    if safety_settings.gender_bias_monitoring:
        prompt_parts.append("- Your language must be free of gender bias.")
    if safety_settings.cultural_bias_detection:
        prompt_parts.append("- Be culturally sensitive and avoid stereotypes.")
    if safety_settings.inclusive_language:
        prompt_parts.append("- You must use inclusive and respectful language at all times.")
    
    return "\n".join(prompt_parts)

def analyze_english_input_eng_only(user_text: str, conversation_stage: str, topic: Optional[str] = None, loop: Optional[asyncio.AbstractEventLoop] = None) -> dict:
    """
    Enhanced multi-stage conversational AI for English learning with consistent Urdu correction
    and specialized logic flows for different learning areas.
    
    Features:
    - Consistent Urdu-to-English correction for every response
    - Separate logic flows for Vocabulary, Sentence Structure, and Topics
    - Fallback to normal NLP conversation outside learning areas
    - Professional error handling and edge case management
    """
    global main_thread_loop
    if loop:
        main_thread_loop = loop

    print(f"🔍 [ENGLISH_ONLY] Analyzing input for stage: {conversation_stage} with topic: {topic}")
    print(f"📝 User input: '{user_text}'")

    # Enhanced base prompt with consistent Urdu correction
    base_prompt = f"""
You are a professional, friendly English tutor AI designed to help learners improve their English skills. 
Your role is to engage in real conversations while providing consistent, gentle corrections.

**CRITICAL: Urdu Input Handling - ALWAYS CORRECT EVERY TIME**
If the user speaks in Urdu, Hindi, or any non-English language:
1. First, provide your conversational response in English
2. Then, ALWAYS add: "By the way, in English you could say, \\"<the English translation of the user's sentence>\\"."
3. This correction must happen EVERY TIME, not just once

**User's spoken text:** "{user_text}"

**Current Conversation Stage:** {conversation_stage}
**Current Topic:** {topic if topic else 'None'}

**Response Format Requirements:**
- Always respond in a warm, encouraging tone
- Provide corrections when needed (grammar, pronunciation, structure)
- Maintain conversation flow naturally
- Use the exact JSON format specified for each stage
"""

    try:
        # Stage-specific logic implementation
        if conversation_stage == "greeting":
            return _handle_greeting_stage(user_text, base_prompt)
        elif conversation_stage == "intent_detection":
            return _handle_intent_detection_stage(user_text, base_prompt)
        elif conversation_stage == "option_selection":
            return _handle_option_selection_stage(user_text, base_prompt)
        elif conversation_stage == "vocabulary_learning":
            return _handle_vocabulary_learning_stage(user_text, base_prompt, topic)
        elif conversation_stage == "sentence_practice":
            return _handle_sentence_practice_stage(user_text, base_prompt, topic)
        elif conversation_stage == "topic_discussion_prompt":
            return _handle_topic_discussion_prompt_stage(user_text, base_prompt)
        elif conversation_stage == "topic_discussion":
            return _handle_topic_discussion_stage(user_text, base_prompt, topic)
        elif conversation_stage == "grammar_focus":
            return _handle_grammar_focus_stage(user_text, base_prompt, topic)
        else:
            # Fallback to normal NLP conversation for unknown stages
            return _handle_fallback_conversation(user_text, base_prompt, conversation_stage)

    except Exception as e:
        print(f"❌ [ENGLISH_ONLY] Critical error during analysis: {str(e)}")
        # Professional fallback response with error logging
        return {
            "conversation_text": f"I'm experiencing a technical difficulty at the moment, but I understood: '{user_text}'. Let's continue our conversation!",
            "next_stage": conversation_stage,
            "needs_correction": False,
            "corrected_sentence": "",
            "correction_type": "none",
            "error_occurred": True,
            "error_message": str(e)
        }

def _handle_greeting_stage(user_text: str, base_prompt: str) -> dict:
    """Handle the initial greeting stage with enhanced Urdu correction"""
    prompt = base_prompt + """
**Task:** This is the user's first response after your greeting. Your goal is to understand their intent and guide them.

**Requirements:**
1. **Language Detection:** Check if the user is speaking in Urdu, Hindi, or English
2. **Consistent Correction:** If non-English, ALWAYS provide the English translation
3. **Intent Analysis:** Understand their learning goal (vocabulary, grammar, speaking, etc.)
4. **Professional Guidance:** Offer clear learning options with encouragement

**Learning Options to Offer:**
- Vocabulary Building
- Sentence Structure & Grammar
- Topic-based Discussion
- Pronunciation Practice
- General Conversation Practice

**JSON Output:**
{
    "conversation_text": "<Your encouraging response with correction if needed, then learning options>",
    "next_stage": "option_selection",
    "needs_correction": <true/false>,
    "corrected_sentence": "<English translation if user spoke in Urdu/Hindi>",
    "correction_type": "<urdu_translation|grammar|pronunciation|structure|none>",
    "detected_language": "<english|urdu|hindi|mixed>",
    "user_intent": "<vocabulary|grammar|speaking|general|unknown>"
}
"""
    
    return _execute_ai_analysis(prompt, "greeting")

def _handle_intent_detection_stage(user_text: str, base_prompt: str) -> dict:
    """Handle intent detection with enhanced analysis"""
    prompt = base_prompt + """
**Task:** Analyze the user's response to understand their specific learning needs and preferences.

**Analysis Requirements:**
1. **Language Assessment:** Determine if they're speaking English, Urdu, or mixed
2. **Learning Preference:** Identify their preferred learning method
3. **Skill Level:** Assess their current English proficiency
4. **Motivation:** Understand their learning goals and motivation

**Response Strategy:**
- Provide immediate correction for any non-English input
- Offer personalized learning path recommendations
- Maintain encouraging and supportive tone
- Set clear expectations for the learning session

**JSON Output:**
{
    "conversation_text": "<Personalized response with corrections and learning path>",
    "next_stage": "option_selection",
    "needs_correction": <true/false>,
    "corrected_sentence": "<English translation if needed>",
    "correction_type": "<urdu_translation|grammar|pronunciation|structure|none>",
    "learning_path": "<vocabulary|grammar|conversation|mixed>",
    "skill_assessment": "<beginner|intermediate|advanced>"
}
"""
    
    return _execute_ai_analysis(prompt, "intent_detection")

def _handle_option_selection_stage(user_text: str, base_prompt: str) -> dict:
    """Handle learning option selection with intelligent routing"""
    prompt = base_prompt + """
**Task:** The user has been offered learning options. Analyze their choice and transition to the appropriate learning path.

**Option Detection:**
1. **Vocabulary Building:** Words, definitions, usage examples
2. **Sentence Structure:** Grammar, sentence formation, syntax
3. **Topic Discussion:** Specific subjects, current events, interests
4. **Pronunciation:** Speaking practice, accent improvement
5. **General Conversation:** Free-flowing English practice

**Intelligent Routing Logic:**
- If "Vocabulary" → next_stage: "vocabulary_learning"
- If "Sentence Structure" or "Grammar" → next_stage: "sentence_practice"
- If "Topic" or "Discussion" → next_stage: "topic_discussion_prompt"
- If "Pronunciation" → next_stage: "pronunciation_practice"
- If unclear → Ask for clarification and remain in "option_selection"

**JSON Output:**
{
    "conversation_text": "<Transition message based on their choice>",
    "next_stage": "<vocabulary_learning|sentence_practice|topic_discussion_prompt|pronunciation_practice|option_selection>",
    "needs_correction": <true/false>,
    "corrected_sentence": "<English translation if needed>",
    "correction_type": "<urdu_translation|grammar|pronunciation|structure|none>",
    "selected_option": "<vocabulary|grammar|topic|pronunciation|unclear>",
    "transition_message": "<Specific transition text>"
}
"""
    
    return _execute_ai_analysis(prompt, "option_selection")

def _handle_vocabulary_learning_stage(user_text: str, base_prompt: str, current_topic: str = None) -> dict:
    """Handle vocabulary learning with specialized logic"""
    # Fix the f-string formatting issue by properly escaping curly braces
    topic_context = current_topic if current_topic else 'General Vocabulary'
    
    prompt = base_prompt + f"""
**Task:** You are in a specialized vocabulary building session. This is NOT general conversation.

**Vocabulary Learning Requirements:**
1. **Word Introduction:** Introduce new vocabulary words relevant to the context
2. **Definition & Usage:** Provide clear definitions and example sentences
3. **Practice Exercises:** Ask user to use words in sentences
4. **Consistent Correction:** ALWAYS correct any non-English input with English translations
5. **Progressive Difficulty:** Gradually increase word complexity based on user progress

**Current Topic Context:** {topic_context}

**Vocabulary Session Flow:**
- Introduce 1-2 new words per interaction
- Provide pronunciation guidance
- Ask for sentence creation using new words
- Give feedback on usage
- Maintain vocabulary focus throughout

**JSON Output:**
{{
    "conversation_text": "<Vocabulary-focused response with new words and exercises>",
    "next_stage": "vocabulary_learning",
    "needs_correction": <true/false>,
    "corrected_sentence": "<English translation if needed>",
    "correction_type": "<urdu_translation|grammar|pronunciation|structure|none>",
    "vocabulary_words": ["<word1>", "<word2>"],
    "learning_activity": "<word_introduction|sentence_practice|definition_review|pronunciation_practice>",
    "session_progress": "<beginning|middle|advanced>"
}}
"""
    
    return _execute_ai_analysis(prompt, "vocabulary_learning")

def _handle_sentence_practice_stage(user_text: str, base_prompt: str, current_topic: str = None) -> dict:
    """Handle sentence practice with grammar focus"""
    # Fix the f-string formatting issue by properly escaping curly braces
    topic_context = current_topic if current_topic else 'General Grammar'
    
    prompt = base_prompt + f"""
**Task:** You are in a specialized sentence structure and grammar practice session. This is NOT general conversation.

**Sentence Practice Requirements:**
1. **Grammar Analysis:** Evaluate sentence structure, verb tense, word order
2. **Immediate Correction:** Provide gentle corrections for grammatical errors
3. **Explanation:** Explain why the correction is needed
4. **Practice Reinforcement:** Ask follow-up questions to reinforce correct usage
5. **Consistent Urdu Correction:** ALWAYS translate any non-English input

**Current Topic Context:** {topic_context}

**Grammar Focus Areas:**
- Subject-verb agreement
- Tense consistency
- Article usage (a, an, the)
- Preposition placement
- Sentence structure

**JSON Output:**
{{
    "conversation_text": "<Grammar-focused response with corrections and practice>",
    "next_stage": "sentence_practice",
    "needs_correction": <true/false>,
    "corrected_sentence": "<Corrected version of user's sentence>",
    "correction_type": "<grammar|tense|structure|article|preposition|none>",
    "grammar_rule": "<Specific grammar rule being practiced>",
    "practice_suggestion": "<Next practice activity>"
}}
"""
    
    return _execute_ai_analysis(prompt, "sentence_practice")

def _handle_topic_discussion_prompt_stage(user_text: str, base_prompt: str) -> dict:
    """Handle topic selection prompt"""
    prompt = base_prompt + """
**Task:** The user wants to discuss a topic. Extract their topic choice and confirm it.

**Topic Extraction Requirements:**
1. **Identify Topic:** Extract the specific topic from user's response
2. **Confirm Choice:** Acknowledge and confirm the selected topic
3. **Engage Interest:** Show enthusiasm for the topic choice
4. **Set Expectations:** Explain how the discussion will proceed
5. **Language Correction:** ALWAYS provide English translations for non-English input

**Topic Discussion Setup:**
- Confirm the topic clearly
- Ask an engaging opening question
- Explain the learning approach for this topic
- Maintain English-only conversation with corrections

**JSON Output:**
{
    "conversation_text": "<Topic confirmation and engagement message>",
    "next_stage": "topic_discussion",
    "needs_correction": <true/false>,
    "corrected_sentence": "<English translation if needed>",
    "correction_type": "<urdu_translation|grammar|pronunciation|structure|none>",
    "extracted_topic": "<The specific topic identified>",
    "discussion_approach": "<How we'll approach this topic>"
}
"""
    
    return _execute_ai_analysis(prompt, "topic_discussion_prompt")

def _handle_topic_discussion_stage(user_text: str, base_prompt: str, current_topic: str) -> dict:
    """Handle ongoing topic discussion with learning focus"""
    prompt = base_prompt + f"""
**Task:** You are in a topic-based discussion about "{current_topic}". This is a learning-focused conversation.

**Topic Discussion Requirements:**
1. **Stay on Topic:** Keep conversation focused on "{current_topic}"
2. **Language Learning:** Use the topic to teach English vocabulary and expressions
3. **Consistent Correction:** ALWAYS correct any non-English input with English translations
4. **Engaging Questions:** Ask relevant follow-up questions to maintain interest
5. **Learning Integration:** Naturally incorporate English learning into the discussion

**Discussion Strategy:**
- Connect user's responses to the topic
- Introduce topic-specific vocabulary
- Practice natural English expressions
- Maintain conversational flow
- Provide gentle corrections when needed

**JSON Output:**
{{
    "conversation_text": "<Topic-focused response with learning elements>",
    "next_stage": "topic_discussion",
    "needs_correction": <true/false>,
    "corrected_sentence": "<English translation if needed>",
    "correction_type": "<urdu_translation|grammar|pronunciation|structure|none>",
    "topic_vocabulary": ["<relevant_word1>", "<relevant_word2>"],
    "discussion_progress": "<beginning|middle|advanced>",
    "next_question": "<Follow-up question to maintain engagement>"
}}
"""
    
    return _execute_ai_analysis(prompt, "topic_discussion")

def _handle_grammar_focus_stage(user_text: str, base_prompt: str, current_topic: str = None) -> dict:
    """Handle grammar-focused learning sessions"""
    # Fix the f-string formatting issue by properly escaping curly braces
    topic_context = current_topic if current_topic else 'General Grammar'
    
    prompt = base_prompt + f"""
**Task:** You are in a specialized grammar learning session. Focus on specific grammar rules and structures.

**Grammar Learning Requirements:**
1. **Rule Explanation:** Clearly explain grammar rules being practiced
2. **Error Correction:** Identify and correct grammatical mistakes
3. **Practice Examples:** Provide examples of correct usage
4. **Progressive Learning:** Build complexity gradually
5. **Consistent Urdu Correction:** ALWAYS translate any non-English input

**Current Topic Context:** {topic_context}

**Grammar Focus Areas:**
- Parts of speech
- Sentence structure
- Verb conjugation
- Tense usage
- Punctuation rules

**JSON Output:**
{{
    "conversation_text": "<Grammar-focused response with rule explanation>",
    "next_stage": "grammar_focus",
    "needs_correction": <true/false>,
    "corrected_sentence": "<Corrected version of user's sentence>",
    "correction_type": "<grammar|tense|structure|punctuation|none>",
    "grammar_rule": "<Specific grammar rule being taught>",
    "practice_examples": ["<example1>", "<example2>"]
}}
"""
    
    return _execute_ai_analysis(prompt, "grammar_focus")

def _handle_fallback_conversation(user_text: str, base_prompt: str, conversation_stage: str) -> dict:
    """Handle unknown stages with fallback to normal NLP conversation"""
    prompt = base_prompt + f"""
**Task:** You are in an unknown conversation stage: "{conversation_stage}". Provide a natural, helpful response.

**Fallback Requirements:**
1. **Natural Response:** Engage in normal conversation
2. **Language Correction:** ALWAYS correct any non-English input
3. **Helpful Guidance:** Offer assistance or clarification
4. **Stage Recovery:** Try to understand what the user needs
5. **Professional Tone:** Maintain helpful and encouraging demeanor

**Response Strategy:**
- Acknowledge the current situation
- Ask clarifying questions if needed
- Provide helpful guidance
- Maintain English learning focus
- Offer to return to structured learning

**JSON Output:**
{
    "conversation_text": "<Natural, helpful response with guidance>",
    "next_stage": "option_selection",
    "needs_correction": <true/false>,
    "corrected_sentence": "<English translation if needed>",
    "correction_type": "<urdu_translation|grammar|pronunciation|structure|none>",
    "fallback_reason": "<Why fallback was triggered>",
    "recovery_suggestion": "<How to return to structured learning>"
}
"""
    
    return _execute_ai_analysis(prompt, "fallback")


def _execute_ai_analysis(prompt: str, stage_name: str) -> dict:
    """
    Execute AI analysis with professional error handling and dynamic settings.
    This is the core function that communicates with the OpenAI API for the
    'English Only' feature, now enhanced to respect dynamic AI Tutor Settings.
    """
    try:
        print(f"🤖 [ENGLISH_ONLY] Executing AI analysis for stage: {stage_name}")

        if not main_thread_loop:
            raise RuntimeError("Event loop not available in thread.")

        # --- Professional Integration of AI Tutor Settings & Safety ---
        # 1. Fetch both AI behavior and safety settings concurrently for efficiency.
        
        # Schedule the coroutines on the main event loop from the current thread
        future_settings = asyncio.run_coroutine_threadsafe(get_ai_settings(), main_thread_loop)
        future_safety_settings = asyncio.run_coroutine_threadsafe(get_ai_safety_settings(), main_thread_loop)

        # Wait for the results
        settings = future_settings.result()
        safety_settings = future_safety_settings.result()
        
        # 2. Build the behavioral prompt using the original, unchanged flow.
        behavioral_prompt = _build_system_prompt_from_settings(prompt, settings)
        
        # 3. Layer the mandatory safety guidelines on top of the behavioral prompt.
        final_prompt = _apply_safety_guidelines(behavioral_prompt, safety_settings)
        
        # 4. Calculate max_tokens from settings. 1 word is roughly 1.5 tokens.
        max_tokens = int(settings.max_response_length * 1.5)
        print(f"⚙️ [SETTINGS] Applying max_response_length: {settings.max_response_length} words (~{max_tokens} tokens)")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": final_prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=max_tokens,  # Apply dynamic token limit
            timeout=30  # 30 second timeout
        )
        
        output = response.choices[0].message.content.strip()
        print(f"✅ [ENGLISH_ONLY] GPT Raw Output for {stage_name}: {output}")
        
        # Parse JSON response with error handling
        try:
            result = json.loads(output)
        except json.JSONDecodeError as json_error:
            print(f"❌ [ENGLISH_ONLY] JSON parsing error for {stage_name}: {json_error}")
            # Return fallback response with error information
            return {
                "conversation_text": f"I'm having trouble processing that response. Let's continue our conversation!",
                "next_stage": "option_selection",
                "needs_correction": False,
                "corrected_sentence": "",
                "correction_type": "none",
                "error_occurred": True,
                "error_type": "json_parsing",
                "original_output": output
            }

        
        # Ensure all required fields are present with defaults
        required_fields = {
            "conversation_text": "Let's continue our conversation!",
            "next_stage": "option_selection",
            "needs_correction": False,
            "corrected_sentence": "",
            "correction_type": "none"
        }
        
        for field, default_value in required_fields.items():
            if field not in result:
                result[field] = default_value
                print(f"⚠️ [ENGLISH_ONLY] Missing field '{field}' for {stage_name}, using default: {default_value}")
        
        # Validate and sanitize the response
        result["conversation_text"] = str(result["conversation_text"]).strip()
        if not result["conversation_text"]:
            result["conversation_text"] = "Let's continue our conversation!"
        
        print(f"✅ [ENGLISH_ONLY] Successfully processed {stage_name} response")
        return result
        
    except Exception as e:
        print(f"❌ [ENGLISH_ONLY] Critical error during AI analysis for {stage_name}: {str(e)}")
        # Return comprehensive fallback response
        return {
            "conversation_text": f"I'm experiencing a technical difficulty at the moment. Let's continue our conversation!",
            "next_stage": "option_selection",
            "needs_correction": False,
            "corrected_sentence": "",
            "correction_type": "none",
            "error_occurred": True,
            "error_type": "ai_execution",
            "error_message": str(e),
            "stage": stage_name
        }

# --- Keep existing helper functions below if they are still needed by other parts of the app ---
# It appears the other functions like get_fluency_feedback are for the Urdu-to-English part,
# so I will leave them untouched.

def get_fluency_feedback_eng(user_text: str, expected_text: str) -> dict:
    """
    Uses GPT to evaluate spoken English against expected sentence,
    returning pronunciation score, tone & intonation (in Urdu), and feedback (in English).
    """
    prompt = f"""
You are an experienced prompt engineer acting as a **kind and encouraging Pakistani female Urdu-speaking teacher** helping a student learn to speak English fluently.
Your feedback must always reflect a **formal yet friendly tone**, like a kind teacher speaking to a child.

Your task is to give **constructive, warm feedback** based only on the student's **spoken attempt** (not spelling or punctuation).  
Your tone should reflect a **formal yet friendly, soft-spoken female teacher**, guiding the learner gently and supportively.

Very Important: Do NOT comment on spelling, capitalization, or punctuation differences at all — ignore these completely. Treat "Where are you" and "where are you?" as identical if spoken that way.
ONLY focus on spoken words — pronunciation, clarity, missing or extra words, tone, and intonation.

ONLY focus on what was heard — pronunciation, clarity, missing or extra words, tone, and intonation.  
Do NOT comment on spelling, punctuation, or written grammar.

🩷 Very Important:  
- Pronunciation score and tone & intonation must still be in **Urdu** as before.  
- But feedback sentence (line 3) must now be in **English**, warm, kind, and clear — like a friendly female teacher encouraging a child.  
- All Urdu terms (like بہترین, درمیانہ) must still be polite, clear, and appropriate — avoid slang — and keep the tone friendly and formal.  
- Use **colloquial, everyday Urdu (بول چال کی زبان)** — but maintain a **formal yet friendly tone** — for lines 1 & 2, and keep feedback (line 3) in simple, kind English.

Respond in **exactly 3 lines**, in this strict format:

Pronunciation score: <percentage>%
Tone & Intonation: بہترین / اچھا / درمیانہ / کمزور  
Feedback: <2-3 short English sentences giving warm, encouraging guidance. Use simple, kind words like "Great job", "Try again", "Well done", etc.>

📋 **Scoring Guide** (internal logic — no need to output this):  
- **70-85%** → Celebrate their success  
- **60-75%** → Mention small mistakes, encourage retry  
- **30-60%** → Gently guide and motivate  
- **0-30%** → Kindly encourage retry with clearer pronunciation

Now evaluate the student's speaking attempt:

**Expected Sentence:** "{expected_text}"  
**Student's Attempt:** "{user_text}"  

Remember:  
✅ Only evaluate what was heard.  
✅ Feedback must sound like a kind, encouraging **female teacher** helping a child learn confidently.  
✅ Always maintain a **formal yet friendly tone** for Urdu parts, and soft, kind tone for English feedback.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        output = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        print("GPT raw output:\n", output)

        # Robust parsing
        result = {}
        lines = [line for line in output.split("\n") if ":" in line]
        for line in lines:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if 'pronunciation' in key:
                result['pronunciation_score'] = value
            elif 'tone' in key:
                result['tone_intonation'] = value
            elif 'feedback' in key:
                result['feedback'] = value

        # Sanity check
        if not result.get("pronunciation_score") or not result.get("feedback"):
            raise ValueError("Invalid GPT response format")

        print("Parsed result: ", result)
        return result

    except Exception as e:
        print("❌ Error during fluency evaluation:", str(e))
        return {
            "pronunciation_score": "0%",
            "tone_intonation": "کمزور",
            "feedback": "Please try again. Speak clearly and confidently."
        }


def get_fluency_feedback(user_text: str, expected_text: str) -> dict:
    """
    Uses GPT to evaluate spoken English against expected sentence,
    returning pronunciation score, tone & intonation, and feedback (in Urdu).
    """
    prompt = f"""
You are an experienced prompt engineer acting as a **kind and encouraging Pakistani female Urdu-speaking teacher** helping a student learn to speak English fluently.
Your feedback must always reflect a **formal yet friendly tone**, like a kind teacher speaking to a child.

Your task is to give **constructive, warm feedback** in **Urdu script**, based only on the student's **spoken attempt** (not spelling or punctuation).  
Your tone should reflect a **formal yet friendly, soft-spoken female teacher**, guiding the learner gently and supportively.

Very Important: Do NOT comment on spelling, capitalization, or punctuation differences at all — ignore these completely. Treat "Where are you" and "where are you?" as identical if spoken that way.
ONLY focus on spoken words — pronunciation, clarity, missing or extra words, tone, and intonation.

ONLY focus on what was heard — pronunciation, clarity, missing or extra words, tone, and intonation.  
Do NOT comment on spelling, punctuation, or written grammar.

🩷 Very Important:   
- Use colloquial, everyday Urdu (بول چال کی زبان) — but maintain a formal yet friendly tone, like a teacher who is respectful yet warm. Avoid overly literary or formal words.
- ✅ Always use "دوہرائیں" (not "دہرائیں") when asking the student to repeat.
- ✅ Do not include the word "جملہ" anywhere in the feedback — instead simply say: "اب دوہرائیں".
- Feedback should be kind, clear, and encouraging — as if helping a child.

Respond in **exactly 3 lines**, in this strict format:

Pronunciation score:<percentage>%
Tone & Intonation:بہترین / اچھا / درمیانہ / کمزور  
Feedback: <2-3 short Urdu sentences giving warm, encouraging guidance. Use simple, everyday words like دوبارہ، بہتر، زبردست، دوہرائیں, etc.>

📋 **Scoring Guide** (internal logic — no need to output this):  
- **70–85%** → Celebrate their success  
- **60–75%** → Mention small mistakes, encourage retry  
- **30–60%** → Gently guide and motivate  
- **0–30%** → Kindly encourage retry with clearer pronunciation

Now evaluate the student's speaking attempt:

**Expected Sentence:** "{expected_text}"  
**Student's Attempt:** "{user_text}"  

Remember:  
✅ Only evaluate what was heard.  
✅ Feedback must sound like a kind, encouraging **female teacher** helping a child learn confidently.
✅ Always maintain a **formal yet friendly tone**.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        output = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        print("GPT raw output:\n", output)

        # Robust parsing
        result = {}
        lines = [line for line in output.split("\n") if ":" in line]
        for line in lines:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if 'pronunciation' in key:
                result['pronunciation_score'] = value
            elif 'tone' in key:
                result['tone_intonation'] = value
            elif 'feedback' in key:
                result['feedback'] = value

        # Sanity check
        if not result.get("pronunciation_score") or not result.get("feedback"):
            raise ValueError("Invalid GPT response format")

        print("Parsed result: ", result)
        return result

    except Exception as e:
        print("❌ Error during fluency evaluation:", str(e))
        return {
            "pronunciation_score": "0%",
            "tone_intonation": "کمزور",
            "feedback": "آئیے دوبارہ کوشش کرتے ہیں۔ صاف صاف بولیں۔"                  
        }

def evaluate_response(expected: str, actual: str) -> dict:
    """
    Wrapper that returns:
    {
        "feedback_text": str (urdu feedback),
        "is_correct": bool,
        "pronunciation_score": str,
        "tone_intonation": str
    }
    """
    print("evaluate_response: ")
    print("Actual: ",actual)
    print("Expected: ",expected)
    print("================================")
    feedback = get_fluency_feedback(actual, expected)

    try:
        score_str = feedback["pronunciation_score"].replace("%", "").strip()
        score = int(score_str)
        is_correct = score >= 80
    except:
        score = 0
        is_correct = False

    feedback_text = feedback["feedback"]
    if score < 80 and "دوبارہ" not in feedback_text:
        feedback_text += " دوبارہ کوشش کریں۔"
    elif score >= 80:
        if "شاباش" not in feedback_text:
            feedback_text += " شاباش!"
        if "آگے بڑھیں" not in feedback_text:
            feedback_text += " آگے بڑھیں۔"
        # Add reminder to speak Urdu for next sentence
        if "اردو میں کچھ کہیں" not in feedback_text:
            feedback_text += " اگلے جملے کے لیے اردو میں کچھ کہیں۔"


    print("✅ is_correct: ", is_correct)

    return {
        "feedback_text": feedback_text,
        "is_correct": is_correct,
        "pronunciation_score": feedback["pronunciation_score"],
        "tone_intonation": feedback["tone_intonation"]
    }

def evaluate_response_eng(expected: str, actual: str) -> dict:
    """
    Wrapper that returns:
    {
        "feedback_text": str (urdu feedback),
        "is_correct": bool,
        "pronunciation_score": str,
        "tone_intonation": str
    }
    """
    print("evaluate_response: ")
    print("Actual: ",actual)
    print("Expected: ",expected)
    print("================================")
    feedback = get_fluency_feedback_eng(actual, expected)

    try:
        score_str = feedback["pronunciation_score"].replace("%", "").strip()
        score = int(score_str)
        is_correct = score >= 80
    except:
        score = 0
        is_correct = False

    feedback_text = feedback["feedback"]
    
    if score < 80 and "try again" not in feedback_text.lower():
        feedback_text += " Let's try again. Speak the sentence clearly."
    elif score >= 80:
        if "great job" not in feedback_text.lower():
            feedback_text += " Great job!"
        if "let's try the next sentence" not in feedback_text.lower():
            feedback_text += " Let's try the next sentence."
        # Add reminder to speak Urdu for next sentence
        if "please say something in urdu" not in feedback_text.lower():
            feedback_text += " Please say something in Urdu"

    
    print("✅ is_correct: ", is_correct)

    return {
        "feedback_text": feedback_text,
        "is_correct": is_correct,
        "pronunciation_score": feedback["pronunciation_score"],
        "tone_intonation": feedback["tone_intonation"]
    }

def evaluate_response_ex1_stage1(expected_phrase: str, user_response: str) -> dict:
    """
    Evaluate the student's response to the expected phrase.
    Returns a structured JSON:
    {
      "feedback": "...",
      "score": int 0-100,
      "is_correct": bool,
      "urdu_used": bool,
      "completed": bool
    }
    """

    prompt = f"""
You are an expert English evaluator for a language learning app.

Your task is to compare the student's response with the expected phrase and return feedback in JSON format only.

📥 Inputs:
- Expected: "{expected_phrase}"
- Student: "{user_response}"

🎯 Evaluate on:
- Accuracy (match in meaning/form)
- Grammar & fluency
- Relevance

🎯 Output JSON format:
{{
  "feedback": "Constructive 1-line feedback",
  "score": integer (0–100),
  "is_correct": true if score >= 80 else false,
  "urdu_used": false,
  "completed": true if score >= 80 else false
}}

📌 Rules:
- Respond ONLY with valid JSON (no commentary or explanation).
- Score ≥ 80 → is_correct: true, completed: true
- Feedback must be helpful and 1 line only.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    # Extract the response
    raw_content = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
    print(f"🔍 [FEEDBACK] Raw GPT response: {raw_content}")

    # Try to extract JSON object even if GPT adds comments
    try:
        # Use regex to extract JSON part only
        json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        json_str = json_match.group(0) if json_match else raw_content
        result = json.loads(json_str)

        # Validation fallback
        required_keys = {"feedback", "score", "is_correct", "urdu_used", "completed"}
        if not required_keys.issubset(result.keys()):
            raise ValueError("Missing keys in GPT response")

        print(f"✅ [FEEDBACK] Parsed result: {result}")
        return result

    except Exception as e:
        print(f"❌ [FEEDBACK] Error: {e}")
        print(f"❌ [FEEDBACK] Raw content: {raw_content}")

        # Fallback default response
        return {
            "feedback": "Good try, but let's improve the accuracy.",
            "score": 50,
            "is_correct": False,
            "urdu_used": False,
            "completed": False
        }
    


def evaluate_response_ex2_stage1(expected_answers: list, user_response: str) -> dict:
    """
    Evaluate the student's response to quick response prompts.
    Returns a structured JSON:
    {
      "feedback": "...",
      "score": int 0-100,
      "is_correct": bool,
      "urdu_used": bool,
      "completed": bool,
      "suggested_improvement": "..."
    }
    """

    prompt = f"""
You are an expert English evaluator for a language learning app specializing in quick response exercises.

Your task is to evaluate the student's response against multiple acceptable answers and provide constructive feedback.

📥 Inputs:
- Expected Answers: {expected_answers}
- Student Response: "{user_response}"

🎯 Evaluation Criteria:
1. **Accuracy**: Does the response match any of the expected answers in meaning?
2. **Grammar**: Is the response grammatically correct?
3. **Fluency**: Is the response natural and fluent?
4. **Relevance**: Does the response appropriately answer the question?

🎯 Output JSON format:
{{
  "feedback": "Constructive 1-2 line feedback in English",
  "score": integer (0–100),
  "is_correct": true if score >= 70 else false,
  "urdu_used": false (always false for this exercise),
  "completed": true if score >= 70 else false,
  "suggested_improvement": "One specific suggestion for improvement"
}}

📌 Scoring Guide:
- 90-100: Perfect or near-perfect response
- 80-89: Very good response with minor issues
- 70-79: Good response with some errors but acceptable
- 60-69: Fair response with noticeable errors
- 50-59: Poor response with significant errors
- 0-49: Very poor or irrelevant response

📌 Rules:
- Respond ONLY with valid JSON (no commentary or explanation).
- Score ≥ 70 → is_correct: true, completed: true
- Feedback must be encouraging and constructive.
- Consider variations in acceptable responses.
- Focus on meaning and communication over perfect grammar.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        # Extract the response
        raw_content = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        print(f"🔍 [FEEDBACK] Raw GPT response for ex2: {raw_content}")

        # Try to extract JSON object even if GPT adds comments
        json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        json_str = json_match.group(0) if json_match else raw_content
        result = json.loads(json_str)

        # Validation fallback
        required_keys = {"feedback", "score", "is_correct", "urdu_used", "completed", "suggested_improvement"}
        if not required_keys.issubset(result.keys()):
            raise ValueError("Missing keys in GPT response")

        print(f"✅ [FEEDBACK] Parsed result for ex2: {result}")
        return result

    except Exception as e:
        print(f"❌ [FEEDBACK] Error in ex2 evaluation: {e}")
        print(f"❌ [FEEDBACK] Raw content: {raw_content}")

        # Fallback default response
        return {
            "feedback": "Good effort! Let's practice more to improve your response.",
            "score": 50,
            "is_correct": False,
            "urdu_used": False,
            "completed": False,
            "suggested_improvement": "Try to match the expected answer more closely."
        }
    


def evaluate_response_ex3_stage1(expected_keywords: list, user_response: str, ai_prompt: str) -> dict:
    """
    Evaluate the student's response to listen and reply prompts.
    Returns a structured JSON:
    {
      "feedback": "...",
      "score": int 0-100,
      "is_correct": bool,
      "urdu_used": bool,
      "completed": bool,
      "suggested_improvement": "...",
      "keyword_matches": int,
      "total_keywords": int
    }
    """

    prompt = f"""
You are an expert English evaluator for a language learning app specializing in listen and reply exercises.

Your task is to evaluate the student's response against expected keywords and provide constructive feedback.

📥 Inputs:
- AI Prompt: "{ai_prompt}"
- Expected Keywords: {expected_keywords}
- Student Response: "{user_response}"

🎯 Evaluation Criteria:
1. **Keyword Recognition**: How many expected keywords are present in the response?
2. **Contextual Relevance**: Does the response appropriately address the AI's prompt?
3. **Grammar & Fluency**: Is the response grammatically correct and natural?
4. **Communication Effectiveness**: Can the response be understood clearly?

🎯 Output JSON format:
{{
  "feedback": "Constructive 1-2 line feedback in English",
  "score": integer (0–100),
  "is_correct": true if score >= 70 else false,
  "urdu_used": false (always false for this exercise),
  "completed": true if score >= 70 else false,
  "suggested_improvement": "One specific suggestion for improvement",
  "keyword_matches": integer (number of keywords found),
  "total_keywords": integer (total number of expected keywords)
}}

📌 Scoring Guide:
- 90-100: Perfect response with all or most keywords and excellent communication
- 80-89: Very good response with most keywords and good communication
- 70-79: Good response with some keywords and acceptable communication
- 60-69: Fair response with few keywords and some communication issues
- 50-59: Poor response with minimal keywords and communication problems
- 0-49: Very poor or irrelevant response

📌 Keyword Matching Rules:
- Count exact matches and close synonyms
- Consider variations in word forms (e.g., "speak" matches "speaking")
- Ignore spelling errors if the word is recognizable
- Focus on meaning over exact spelling

📌 Rules:
- Respond ONLY with valid JSON (no commentary or explanation).
- Score ≥ 70 → is_correct: true, completed: true
- Feedback must be encouraging and constructive.
- Consider the context of the AI prompt when evaluating relevance.
- Focus on communication effectiveness over perfect grammar.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        # Extract the response
        raw_content = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        print(f"🔍 [FEEDBACK] Raw GPT response for ex3: {raw_content}")

        # Try to extract JSON object even if GPT adds comments
        json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        json_str = json_match.group(0) if json_match else raw_content
        result = json.loads(json_str)

        # Validation fallback
        required_keys = {"feedback", "score", "is_correct", "urdu_used", "completed", "suggested_improvement", "keyword_matches", "total_keywords"}
        if not required_keys.issubset(result.keys()):
            raise ValueError("Missing keys in GPT response")

        print(f"✅ [FEEDBACK] Parsed result for ex3: {result}")
        return result

    except Exception as e:
        print(f"❌ [FEEDBACK] Error in ex3 evaluation: {e}")
        print(f"❌ [FEEDBACK] Raw content: {raw_content}")

        # Fallback default response
        return {
            "feedback": "Good effort! Let's practice more to improve your response.",
            "score": 50,
            "is_correct": False,
            "urdu_used": False,
            "completed": False,
            "suggested_improvement": "Try to include more of the expected keywords in your response.",
            "keyword_matches": 0,
            "total_keywords": len(expected_keywords)
        }



def evaluate_response_ex1_stage2(expected_keywords: list, user_response: str, phrase: str, example: str) -> dict:
    """
    Evaluate the student's response to daily routine narration prompts.
    Returns a structured JSON:
    {
      "feedback": "...",
      "score": int 0-100,
      "is_correct": bool,
      "urdu_used": bool,
      "completed": bool,
      "suggested_improvement": "...",
      "keyword_matches": int,
      "total_keywords": int,
      "fluency_score": int,
      "grammar_score": int
    }
    """

    prompt = f"""
You are an expert English evaluator for a language learning app specializing in daily routine narration exercises.

Your task is to evaluate the student's response against expected keywords and provide comprehensive feedback.

📥 Inputs:
- Phrase: "{phrase}"
- Example: "{example}"
- Expected Keywords: {expected_keywords}
- Student Response: "{user_response}"

🎯 Evaluation Criteria:
1. **Keyword Recognition**: How many expected keywords are present in the response?
2. **Contextual Relevance**: Does the response appropriately address the daily routine question?
3. **Grammar & Structure**: Is the response grammatically correct and well-structured?
4. **Fluency & Naturalness**: Does the response sound natural and fluent?
5. **Content Completeness**: Does the response provide sufficient detail about daily routines?

🎯 Output JSON format:
{{
  "feedback": "Constructive 2-3 line feedback in English",
  "score": integer (0–100),
  "is_correct": true if score >= 75 else false,
  "urdu_used": false (always false for this exercise),
  "completed": true if score >= 75 else false,
  "suggested_improvement": "One specific suggestion for improvement",
  "keyword_matches": integer (number of keywords found),
  "total_keywords": integer (total number of expected keywords),
  "fluency_score": integer (0-100, based on naturalness and flow),
  "grammar_score": integer (0-100, based on grammatical accuracy)
}}

📌 Scoring Guide:
- 90-100: Excellent response with all keywords, perfect grammar, and natural fluency
- 80-89: Very good response with most keywords and good grammar/fluency
- 75-79: Good response with some keywords and acceptable grammar/fluency
- 65-74: Fair response with few keywords and some grammar/fluency issues
- 50-64: Poor response with minimal keywords and significant issues
- 0-49: Very poor or irrelevant response

📌 Keyword Matching Rules:
- Count exact matches and close synonyms
- Consider variations in word forms (e.g., "wake" matches "waking", "woke")
- Ignore spelling errors if the word is recognizable
- Focus on meaning over exact spelling
- Consider context-specific usage

📌 Grammar & Fluency Assessment:
- Grammar Score: Evaluate sentence structure, verb tenses, articles, prepositions
- Fluency Score: Assess natural flow, appropriate vocabulary, logical sequence
- Consider typical daily routine vocabulary and expressions
- Reward use of time expressions (first, then, after that, usually, etc.)

📌 Rules:
- Respond ONLY with valid JSON (no commentary or explanation).
- Score ≥ 75 → is_correct: true, completed: true
- Feedback must be encouraging and constructive.
- Consider the context of daily routine questions.
- Focus on practical communication over perfect grammar.
- Reward natural, conversational responses.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        # Extract the response
        raw_content = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        print(f"🔍 [FEEDBACK] Raw GPT response for ex1_stage2: {raw_content}")

        # Try to extract JSON object even if GPT adds comments
        json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        json_str = json_match.group(0) if json_match else raw_content
        result = json.loads(json_str)

        # Validation fallback
        required_keys = {"feedback", "score", "is_correct", "urdu_used", "completed", "suggested_improvement", "keyword_matches", "total_keywords", "fluency_score", "grammar_score"}
        if not required_keys.issubset(result.keys()):
            raise ValueError("Missing keys in GPT response")

        print(f"✅ [FEEDBACK] Parsed result for ex1_stage2: {result}")
        return result

    except Exception as e:
        print(f"❌ [FEEDBACK] Error in ex1_stage2 evaluation: {e}")
        print(f"❌ [FEEDBACK] Raw content: {raw_content}")

        # Fallback default response
        return {
            "feedback": "Good effort! Try to include more details about your daily routine and use the suggested keywords.",
            "score": 50,
            "is_correct": False,
            "urdu_used": False,
            "completed": False,
            "suggested_improvement": "Try to include more of the expected keywords in your response.",
            "keyword_matches": 0,
            "total_keywords": len(expected_keywords),
            "fluency_score": 50,
            "grammar_score": 50
        }



def evaluate_response_ex2_stage2(expected_answers: list, user_response: str, question: str, question_urdu: str) -> dict:
    """
    Evaluate the student's response to quick answer prompts in Stage 2.
    Returns a structured JSON:
    {
      "feedback": "...",
      "score": int 0-100,
      "is_correct": bool,
      "urdu_used": bool,
      "completed": bool,
      "suggested_improvement": "...",
      "answer_accuracy": int,
      "grammar_score": int,
      "fluency_score": int
    }
    """

    prompt = f"""
You are an expert English evaluator for a language learning app specializing in quick answer exercises for Stage 2 learners.

Your task is to evaluate the student's response against multiple acceptable answers and provide comprehensive feedback.

📥 Inputs:
- Question: "{question}"
- Question (Urdu): "{question_urdu}"
- Expected Answers: {expected_answers}
- Student Response: "{user_response}"

🎯 Evaluation Criteria:
1. **Answer Accuracy**: Does the response match any of the expected answers in meaning and content?
2. **Grammar & Structure**: Is the response grammatically correct and well-structured?
3. **Fluency & Naturalness**: Does the response sound natural and conversational?
4. **Relevance**: Does the response appropriately answer the question asked?
5. **Completeness**: Does the response provide sufficient information?

🎯 Output JSON format:
{{
  "feedback": "Constructive 2-3 line feedback in English",
  "score": integer (0–100),
  "is_correct": true if score >= 75 else false,
  "urdu_used": false (always false for this exercise),
  "completed": true if score >= 75 else false,
  "suggested_improvement": "One specific suggestion for improvement",
  "answer_accuracy": integer (0-100, based on how well the answer matches expected responses),
  "grammar_score": integer (0-100, based on grammatical accuracy),
  "fluency_score": integer (0-100, based on naturalness and flow)
}}

📌 Scoring Guide:
- 90-100: Excellent response that perfectly matches expected answers with natural fluency
- 80-89: Very good response with minor variations but excellent communication
- 75-79: Good response that effectively communicates the intended meaning
- 65-74: Fair response with some errors but generally understandable
- 50-64: Poor response with significant errors or lack of relevance
- 0-49: Very poor or irrelevant response

📌 Answer Matching Rules:
- Accept variations in wording while maintaining the same meaning
- Consider synonyms and alternative expressions
- Allow for personal variations (e.g., different cities, preferences)
- Focus on communication effectiveness over exact word matching
- Consider cultural context and personal experiences

📌 Grammar & Fluency Assessment:
- Grammar Score: Evaluate sentence structure, verb tenses, articles, prepositions
- Fluency Score: Assess natural flow, appropriate vocabulary, conversational tone
- Consider typical question-answer patterns in English
- Reward natural, everyday language use

📌 Rules:
- Respond ONLY with valid JSON (no commentary or explanation).
- Score ≥ 75 → is_correct: true, completed: true
- Feedback must be encouraging and constructive.
- Consider the context of the question when evaluating relevance.
- Focus on practical communication over perfect grammar.
- Reward natural, conversational responses that effectively answer the question.
- Consider cultural and personal variations in responses.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        # Extract the response
        raw_content = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        print(f"🔍 [FEEDBACK] Raw GPT response for ex2_stage2: {raw_content}")

        # Try to extract JSON object even if GPT adds comments
        json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        json_str = json_match.group(0) if json_match else raw_content
        result = json.loads(json_str)

        # Validation fallback
        required_keys = {"feedback", "score", "is_correct", "urdu_used", "completed", "suggested_improvement", "answer_accuracy", "grammar_score", "fluency_score"}
        if not required_keys.issubset(result.keys()):
            raise ValueError("Missing keys in GPT response")

        print(f"✅ [FEEDBACK] Parsed result for ex2_stage2: {result}")
        return result

    except Exception as e:
        print(f"❌ [FEEDBACK] Error in ex2_stage2 evaluation: {e}")
        print(f"❌ [FEEDBACK] Raw content: {raw_content}")

        # Fallback default response
        return {
            "feedback": "Good effort! Try to answer the question more completely and naturally.",
            "score": 50,
            "is_correct": False,
            "urdu_used": False,
            "completed": False,
            "suggested_improvement": "Try to match the expected answer format more closely.",
            "answer_accuracy": 50,
            "grammar_score": 50,
            "fluency_score": 50
        }
    

def evaluate_response_ex3_stage2(conversation_history: list, scenario_context: str, expected_keywords: list, ai_character: str) -> dict:
    """
    Evaluate roleplay simulation conversation for Stage 2, Exercise 3
    Uses GPT-4o to analyze conversation quality, keyword usage, and learning progress
    """
    try:
        # Format conversation history for analysis
        conversation_text = ""
        user_messages = []
        
        for message in conversation_history:
            if message.get("role") == "user":
                user_messages.append(message.get("content", ""))
                conversation_text += f"User: {message.get('content', '')}\n"
            elif message.get("role") == "assistant":
                conversation_text += f"AI ({ai_character}): {message.get('content', '')}\n"
        
        # Create comprehensive evaluation prompt
        evaluation_prompt = f"""
You are an expert English language tutor evaluating a roleplay simulation conversation. 
The student is practicing English through a realistic scenario: {scenario_context}

CONVERSATION HISTORY:
{conversation_text}

EVALUATION CRITERIA:
1. **Conversation Flow**: Natural dialogue progression, appropriate responses
2. **Keyword Usage**: Student should use expected keywords: {', '.join(expected_keywords)}
3. **Grammar & Fluency**: Correct sentence structure, natural expression
4. **Cultural Appropriateness**: Responses fit the scenario context
5. **Learning Engagement**: Active participation, meaningful interaction

EXPECTED KEYWORDS: {expected_keywords}
AI CHARACTER: {ai_character}
SCENARIO: {scenario_context}

Please provide a detailed evaluation in the following JSON format:
{{
    "overall_score": <score_0_100>,
    "is_correct": <true_if_score_above_70>,
    "completed": <true_if_conversation_has_natural_ending>,
    "conversation_flow_score": <score_0_100>,
    "keyword_usage_score": <score_0_100>,
    "grammar_fluency_score": <score_0_100>,
    "cultural_appropriateness_score": <score_0_100>,
    "engagement_score": <score_0_100>,
    "keyword_matches": <list_of_used_keywords>,
    "total_keywords_expected": <number>,
    "keywords_used_count": <number>,
    "grammar_errors": <list_of_grammar_issues>,
    "fluency_issues": <list_of_fluency_problems>,
    "strengths": <list_of_positive_aspects>,
    "areas_for_improvement": <list_of_improvement_suggestions>,
    "suggested_improvement": <specific_improvement_advice>,
    "conversation_quality": <"excellent"|"good"|"fair"|"needs_improvement">,
    "learning_progress": <"significant"|"moderate"|"minimal"|"none">,
    "recommendations": <list_of_next_steps>
}}

Focus on:
- Natural conversation flow and appropriate responses
- Usage of expected keywords in context
- Grammar accuracy and fluency
- Cultural appropriateness for the scenario
- Overall learning engagement and progress
"""

        print(f"🔄 [FEEDBACK] Evaluating roleplay conversation for scenario: {scenario_context}")
        print(f"📊 [FEEDBACK] Conversation length: {len(conversation_history)} messages")
        print(f"🎯 [FEEDBACK] Expected keywords: {expected_keywords}")
        
        # Call OpenAI GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert English language tutor specializing in roleplay simulations and conversation evaluation. Provide detailed, constructive feedback in the exact JSON format requested."
                },
                {
                    "role": "user", 
                    "content": evaluation_prompt
                }
            ],
            temperature=0.3,
            max_tokens=2000
        )

        # Parse the response
        evaluation_text = response.choices[0].message.content.strip()
        print(f"✅ [FEEDBACK] Raw evaluation response received: {len(evaluation_text)} characters")
        
        # Extract JSON from response
        try:
            # Find JSON content in the response
            start_idx = evaluation_text.find('{')
            end_idx = evaluation_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_content = evaluation_text[start_idx:end_idx]
                evaluation = json.loads(json_content)
            else:
                raise ValueError("No JSON content found in response")
                
        except json.JSONDecodeError as e:
            print(f"❌ [FEEDBACK] JSON parsing error: {str(e)}")
            print(f"📝 [FEEDBACK] Raw response: {evaluation_text}")
            
            # Fallback evaluation
            evaluation = {
                "overall_score": 60,
                "is_correct": False,
                "completed": len(conversation_history) >= 4,
                "conversation_flow_score": 60,
                "keyword_usage_score": 50,
                "grammar_fluency_score": 60,
                "cultural_appropriateness_score": 70,
                "engagement_score": 65,
                "keyword_matches": [],
                "total_keywords_expected": len(expected_keywords),
                "keywords_used_count": 0,
                "grammar_errors": ["Evaluation parsing error"],
                "fluency_issues": ["Unable to analyze"],
                "strengths": ["Conversation attempted"],
                "areas_for_improvement": ["Please try again"],
                "suggested_improvement": "Please try the roleplay again for better evaluation.",
                "conversation_quality": "needs_improvement",
                "learning_progress": "minimal",
                "recommendations": ["Retry the conversation"]
            }

        # Validate and normalize scores
        # The original code had a validate_and_normalize_evaluation function,
        # but it was not defined in the provided context.
        # Assuming a simple validation and normalization for now.
        evaluation["overall_score"] = min(100, max(0, evaluation.get("overall_score", 0)))
        evaluation["conversation_flow_score"] = min(100, max(0, evaluation.get("conversation_flow_score", 0)))
        evaluation["keyword_usage_score"] = min(100, max(0, evaluation.get("keyword_usage_score", 0)))
        evaluation["grammar_fluency_score"] = min(100, max(0, evaluation.get("grammar_fluency_score", 0)))
        evaluation["cultural_appropriateness_score"] = min(100, max(0, evaluation.get("cultural_appropriateness_score", 0)))
        evaluation["engagement_score"] = min(100, max(0, evaluation.get("engagement_score", 0)))

        print(f"✅ [FEEDBACK] Evaluation completed successfully")
        print(f"📊 [FEEDBACK] Overall score: {evaluation.get('overall_score', 0)}")
        print(f"🎯 [FEEDBACK] Keywords used: {evaluation.get('keywords_used_count', 0)}/{evaluation.get('total_keywords_expected', 0)}")
        print(f"✅ [FEEDBACK] Is correct: {evaluation.get('is_correct', False)}")
        print(f"🏁 [FEEDBACK] Completed: {evaluation.get('completed', False)}")
        
        return evaluation

    except Exception as e:
        print(f"❌ [FEEDBACK] Error in evaluate_response_ex3_stage2: {str(e)}")
        return {
            "overall_score": 50,
            "is_correct": False,
            "completed": False,
            "conversation_flow_score": 50,
            "keyword_usage_score": 50,
            "grammar_fluency_score": 50,
            "cultural_appropriateness_score": 50,
            "engagement_score": 50,
            "keyword_matches": [],
            "total_keywords_expected": len(expected_keywords),
            "keywords_used_count": 0,
            "grammar_errors": [f"Evaluation error: {str(e)}"],
            "fluency_issues": ["Unable to evaluate"],
            "strengths": ["Attempted conversation"],
            "areas_for_improvement": ["System error occurred"],
            "suggested_improvement": "Please try again later.",
            "conversation_quality": "needs_improvement",
            "learning_progress": "none",
            "recommendations": ["Retry after system restart"]
        }



def evaluate_response_ex1_stage3(expected_keywords: list, user_response: str, prompt: str, prompt_urdu: str, model_answer: str) -> dict:
    """
    Evaluate user's storytelling response for Stage 3 Exercise 1
    Uses ChatGPT to provide comprehensive feedback on narrative structure, past tense usage, and fluency
    """
    print(f"🔄 [EVAL] Evaluating Stage 3 Exercise 1 response")
    print(f"📝 [EVAL] User response: '{user_response}'")
    print(f"🎯 [EVAL] Expected keywords: {expected_keywords}")
    print(f"📖 [EVAL] Prompt: '{prompt}'")
    print(f"📖 [EVAL] Model answer: '{model_answer}'")
    
    try:
        # Create comprehensive evaluation prompt
        evaluation_prompt = f"""
You are an expert English language tutor evaluating a student's storytelling response. The student is learning to tell personal stories in English.

**STUDENT'S PROMPT:** {prompt}
**STUDENT'S RESPONSE:** "{user_response}"
**MODEL ANSWER FOR REFERENCE:** "{model_answer}"
**EXPECTED KEYWORDS TO INCLUDE:** {expected_keywords}

**EVALUATION CRITERIA:**
1. **Past Tense Usage (25 points):** Check if the student correctly uses past tense verbs (was, were, had, went, felt, etc.)
2. **Narrative Structure (25 points):** Evaluate if the story has a clear beginning, middle, and end with proper transitions
3. **Keyword Integration (20 points):** Assess how well the student incorporates the expected keywords naturally
4. **Fluency & Coherence (20 points):** Check for smooth flow, logical progression, and clear expression
5. **Descriptive Language (10 points):** Evaluate use of descriptive words and emotional expression

**SCORING GUIDELINES:**
- 90-100: Excellent storytelling with all criteria met
- 80-89: Very good with minor issues
- 70-79: Good with some areas for improvement
- 60-69: Satisfactory but needs work
- Below 60: Needs significant improvement

**TASK:** Provide a comprehensive evaluation with specific feedback and suggestions for improvement.

**REQUIRED JSON OUTPUT FORMAT:**
{{
    "score": <number between 0-100>,
    "is_correct": <boolean - true if score >= 75>,
    "completed": <boolean - true if score >= 80>,
    "keyword_matches": <number of expected keywords found>,
    "total_keywords": <total number of expected keywords>,
    "fluency_score": <number between 0-100>,
    "grammar_score": <number between 0-100>,
    "detailed_feedback": {{
        "past_tense_usage": "<specific feedback on past tense usage>",
        "narrative_structure": "<feedback on story structure and flow>",
        "keyword_integration": "<feedback on keyword usage>",
        "fluency_coherence": "<feedback on overall fluency>",
        "descriptive_language": "<feedback on descriptive elements>"
    }},
    "suggested_improvement": "<specific suggestions for improvement>",
    "strengths": ["<list of strengths in the response>"],
    "areas_for_improvement": ["<list of areas that need work>"]
}}
"""

        print(f"🤖 [EVAL] Sending evaluation request to ChatGPT...")
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert English language tutor specializing in storytelling and narrative skills. Provide detailed, constructive feedback in JSON format."
                },
                {
                    "role": "user",
                    "content": evaluation_prompt
                }
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        print(f"✅ [EVAL] Received ChatGPT response")
        
        # Extract and parse the response
        evaluation_text = response.choices[0].message.content.strip()
        print(f"📄 [EVAL] Raw evaluation response: {evaluation_text}")
        
        # Try to extract JSON from the response
        try:
            # Look for JSON in the response
            json_start = evaluation_text.find('{')
            json_end = evaluation_text.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_content = evaluation_text[json_start:json_end]
                evaluation_result = json.loads(json_content)
                print(f"✅ [EVAL] Successfully parsed JSON evaluation")
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            print(f"❌ [EVAL] JSON parsing error: {str(e)}")
            print(f"📄 [EVAL] Attempted to parse: {evaluation_text}")
            
            # Fallback evaluation
            evaluation_result = {
                "score": 50,
                "is_correct": False,
                "completed": False,
                "keyword_matches": 0,
                "total_keywords": len(expected_keywords),
                "fluency_score": 50,
                "grammar_score": 50,
                "detailed_feedback": {
                    "past_tense_usage": "Unable to evaluate due to processing error",
                    "narrative_structure": "Unable to evaluate due to processing error",
                    "keyword_integration": "Unable to evaluate due to processing error",
                    "fluency_coherence": "Unable to evaluate due to processing error",
                    "descriptive_language": "Unable to evaluate due to processing error"
                },
                "suggested_improvement": "Please try again. Make sure to use past tense verbs and tell a complete story with beginning, middle, and end.",
                "strengths": ["Response provided"],
                "areas_for_improvement": ["Evaluation processing error"]
            }
        
        # Validate and sanitize the evaluation result
        score = evaluation_result.get("score", 50)
        if not isinstance(score, (int, float)) or score < 0 or score > 100:
            score = 50
            evaluation_result["score"] = score
        
        is_correct = evaluation_result.get("is_correct", score >= 75)
        completed = evaluation_result.get("completed", score >= 80)
        
        # Ensure keyword matches is valid
        keyword_matches = evaluation_result.get("keyword_matches", 0)
        total_keywords = evaluation_result.get("total_keywords", len(expected_keywords))
        
        if not isinstance(keyword_matches, int) or keyword_matches < 0:
            keyword_matches = 0
        if not isinstance(total_keywords, int) or total_keywords <= 0:
            total_keywords = len(expected_keywords)
        
        evaluation_result.update({
            "is_correct": is_correct,
            "completed": completed,
            "keyword_matches": keyword_matches,
            "total_keywords": total_keywords
        })
        
        print(f"📊 [EVAL] Final evaluation result:")
        print(f"   - Score: {score}")
        print(f"   - Is correct: {is_correct}")
        print(f"   - Completed: {completed}")
        print(f"   - Keyword matches: {keyword_matches}/{total_keywords}")
        print(f"   - Fluency score: {evaluation_result.get('fluency_score', 0)}")
        print(f"   - Grammar score: {evaluation_result.get('grammar_score', 0)}")
        
        return evaluation_result
        
    except Exception as e:
        print(f"❌ [EVAL] Error in evaluate_response_ex1_stage3: {str(e)}")
        
        # Return fallback evaluation
        return {
            "score": 50,
            "is_correct": False,
            "completed": False,
            "keyword_matches": 0,
            "total_keywords": len(expected_keywords),
            "fluency_score": 50,
            "grammar_score": 50,
            "detailed_feedback": {
                "past_tense_usage": "Evaluation error occurred",
                "narrative_structure": "Evaluation error occurred",
                "keyword_integration": "Evaluation error occurred",
                "fluency_coherence": "Evaluation error occurred",
                "descriptive_language": "Evaluation error occurred"
            },
            "suggested_improvement": "Please try again. Focus on using past tense verbs and telling a complete story.",
            "strengths": ["Attempted response"],
            "areas_for_improvement": ["Technical evaluation error"]
        }


def evaluate_response_ex2_stage3(expected_responses: list, user_response: str, context: str, initial_prompt: str, follow_up_turns: list) -> dict:
    """
    Evaluate user's response for Stage 3 Exercise 2 (Group Dialogue) using OpenAI GPT-4.
    Focuses on conversational flow, agreement/disagreement expressions, and group decision-making.
    """
    print(f"🔍 [EVAL] Evaluating group dialogue response: {user_response[:50]}...")
    
    # Extract expected response types and keywords
    expected_types = [resp.get("type", "") for resp in expected_responses]
    all_keywords = []
    for resp in expected_responses:
        all_keywords.extend(resp.get("keywords", []))
    
    # Create conversation context
    conversation_context = f"""
**Initial Prompt:** {initial_prompt}
"""
    for turn in follow_up_turns:
        conversation_context += f"""
**{turn['speaker']}:** {turn['message']}"""
    
    prompt_template = f"""
You are an expert English language tutor evaluating a student's group dialogue response for Stage 3 (B1 Intermediate level).

**Context:**
- Exercise: Group Dialogue with AI Personas
- Student Level: B1 Intermediate
- Focus: Conversational flow, agreement/disagreement, group decision-making

**Conversation Context:**
{conversation_context}

**Student's Response:** "{user_response}"

**Expected Response Types:** {expected_types}
**Expected Keywords:** {all_keywords}

**Evaluation Criteria:**
1. **Relevance to Conversation (25%):** Response directly addresses the question and maintains conversation flow
2. **Appropriate Expressions (25%):** Uses proper agreement/disagreement phrases and opinion expressions
3. **Fluency and Tone (20%):** Natural flow, polite tone, clear pronunciation
4. **Conversation Timing (15%):** Responds appropriately without interrupting flow
5. **Group Decision Language (15%):** Uses collaborative language and decision-making phrases

**Scoring System:**
- Excellent (90-100%): All criteria met with high quality
- Good (75-89%): Most criteria met with minor issues
- Fair (60-74%): Some criteria met with noticeable issues
- Needs Improvement (Below 60%): Significant issues in multiple areas

**Instructions:**
Analyze the student's response comprehensively and provide detailed feedback.
Focus on conversational skills and group interaction abilities.

**Output Format (JSON):**
{{
    "overall_score": <0-100>,
    "relevance_score": <0-25>,
    "expressions_score": <0-25>,
    "fluency_score": <0-20>,
    "timing_score": <0-15>,
    "decision_language_score": <0-15>,
    "keyword_matches": <list of matched keywords>,
    "total_keywords": <total number of expected keywords>,
    "matched_keywords_count": <number of matched keywords>,
    "response_type_detected": "<agreement/disagreement/compromise/etc>",
    "detailed_feedback": {{
        "relevance_feedback": "<specific feedback on conversation relevance>",
        "expressions_feedback": "<feedback on agreement/disagreement expressions>",
        "fluency_feedback": "<feedback on fluency and tone>",
        "timing_feedback": "<feedback on conversation timing>",
        "decision_language_feedback": "<feedback on group decision language>"
    }},
    "suggested_improvements": [
        "<specific improvement suggestion 1>",
        "<specific improvement suggestion 2>",
        "<specific improvement suggestion 3>"
    ],
    "encouragement": "<positive encouragement message>",
    "next_steps": "<what to focus on next>"
}}
"""

    try:
        print("🔄 [EVAL] Sending evaluation request to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert English language tutor specializing in B1 intermediate level conversational assessment."},
                {"role": "user", "content": prompt_template}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content
        print(f"📊 [EVAL] Raw OpenAI response: {result_text[:200]}...")
        
        # Clean the response text to extract JSON
        result_text = result_text.strip()
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        print(f"📊 [EVAL] Cleaned response: {result_text[:200]}...")
        
        # Parse JSON response
        evaluation_result = json.loads(result_text)
        
        # Calculate success based on overall score
        success = evaluation_result.get("overall_score", 0) >= 75
        
        print(f"✅ [EVAL] Evaluation completed. Score: {evaluation_result.get('overall_score', 0)}%")
        
        return {
            "success": success,
            "evaluation": evaluation_result,
            "suggested_improvement": evaluation_result.get("suggested_improvements", [""])[0] if evaluation_result.get("suggested_improvements") else "",
            "keyword_matches": evaluation_result.get("keyword_matches", []),
            "total_keywords": evaluation_result.get("total_keywords", 0),
            "matched_keywords_count": evaluation_result.get("matched_keywords_count", 0),
            "fluency_score": evaluation_result.get("fluency_score", 0),
            "grammar_score": evaluation_result.get("expressions_score", 0) + evaluation_result.get("decision_language_score", 0),
            "response_type": evaluation_result.get("response_type_detected", ""),
            "score": evaluation_result.get("overall_score", 0),
            "is_correct": success,
            "completed": success
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ [EVAL] JSON parsing error: {str(e)}")
        print(f"📊 [EVAL] Failed to parse response: {result_text}")
        fallback_evaluation = {
            "overall_score": 50,
            "relevance_score": 12,
            "expressions_score": 12,
            "fluency_score": 10,
            "timing_score": 8,
            "decision_language_score": 8,
            "keyword_matches": [],
            "total_keywords": len(all_keywords),
            "matched_keywords_count": 0,
            "response_type_detected": "unknown",
            "detailed_feedback": {
                "relevance_feedback": "Response was received but could not be fully evaluated.",
                "expressions_feedback": "Please try to use clear agreement or disagreement phrases.",
                "fluency_feedback": "Speak clearly and naturally.",
                "timing_feedback": "Respond appropriately to the conversation flow.",
                "decision_language_feedback": "Use collaborative language when making decisions."
            },
            "suggested_improvements": [
                "Try to be more specific in your response",
                "Use clear agreement or disagreement phrases",
                "Practice natural conversation flow"
            ],
            "encouragement": "Good effort! Keep practicing to improve your conversational skills.",
            "next_steps": "Focus on using appropriate expressions for group discussions."
        }
        
        return {
            "success": False,
            "error": "Failed to parse evaluation response",
            "suggested_improvement": "Please try again with a clearer response.",
            "evaluation": fallback_evaluation,
            "score": 50,
            "is_correct": False,
            "completed": False,
            "keyword_matches": [],
            "total_keywords": len(all_keywords),
            "matched_keywords_count": 0,
            "fluency_score": 10,
            "grammar_score": 20,
            "response_type": "unknown"
        }
    except Exception as e:
        print(f"❌ [EVAL] OpenAI API error: {str(e)}")
        fallback_evaluation = {
            "overall_score": 50,
            "relevance_score": 12,
            "expressions_score": 12,
            "fluency_score": 10,
            "timing_score": 8,
            "decision_language_score": 8,
            "keyword_matches": [],
            "total_keywords": len(all_keywords),
            "matched_keywords_count": 0,
            "response_type_detected": "unknown",
            "detailed_feedback": {
                "relevance_feedback": "Response was received but could not be fully evaluated.",
                "expressions_feedback": "Please try to use clear agreement or disagreement phrases.",
                "fluency_feedback": "Speak clearly and naturally.",
                "timing_feedback": "Respond appropriately to the conversation flow.",
                "decision_language_feedback": "Use collaborative language when making decisions."
            },
            "suggested_improvements": [
                "Try to be more specific in your response",
                "Use clear agreement or disagreement phrases",
                "Practice natural conversation flow"
            ],
            "encouragement": "Good effort! Keep practicing to improve your conversational skills.",
            "next_steps": "Focus on using appropriate expressions for group discussions."
        }
        
        return {
            "success": False,
            "error": f"Evaluation service error: {str(e)}",
            "suggested_improvement": "Please try again later.",
            "evaluation": fallback_evaluation,
            "score": 50,
            "is_correct": False,
            "completed": False,
            "keyword_matches": [],
            "total_keywords": len(all_keywords),
            "matched_keywords_count": 0,
            "fluency_score": 10,
            "grammar_score": 20,
            "response_type": "unknown"
        }


def evaluate_response_ex3_stage3(expected_keywords: list, user_response: str, problem_description: str, context: str, polite_phrases: list, sample_responses: list) -> dict:
    """
    Evaluate user's response for Stage 3 Exercise 3 (Problem-Solving Simulations) using OpenAI GPT-4o.
    Focuses on polite problem-solving language, clarity, and functional English usage.
    """
    print(f"🔍 [EVAL] Evaluating problem-solving response: {user_response[:50]}...")
    
    # Create comprehensive prompt for evaluation
    prompt_template = f"""
You are an expert English language tutor specializing in B1 intermediate level problem-solving assessment. You are a well experienced prompt engineer.

**Problem Scenario:**
{problem_description}

**Context:**
{context}

**User's Response:**
"{user_response}"

**Expected Keywords (should be included):**
{', '.join(expected_keywords)}

**Polite Phrases to Use:**
{', '.join(polite_phrases)}

**Sample Good Responses:**
{', '.join(sample_responses)}

**Evaluation Criteria:**
1. **Clarity (20 points):** Clear description of the problem and situation
2. **Politeness (25 points):** Use of polite phrases and respectful tone
3. **Request Structure (20 points):** Proper way to ask for help or assistance
4. **Specificity (15 points):** Providing specific details about the issue
5. **Solution Orientation (20 points):** Asking for specific solutions or next steps

**Task:** Evaluate the user's response based on the criteria above. Provide detailed feedback and scoring.

**JSON Output Format:**
{{
    "overall_score": <0-100>,
    "clarity_score": <0-20>,
    "politeness_score": <0-25>,
    "request_structure_score": <0-20>,
    "specificity_score": <0-15>,
    "solution_orientation_score": <0-20>,
    "keyword_matches": ["list", "of", "matched", "keywords"],
    "total_keywords": <number>,
    "matched_keywords_count": <number>,
    "response_type_detected": "<apology|request|complaint|notification>",
    "detailed_feedback": {{
        "clarity_feedback": "<feedback on clarity>",
        "politeness_feedback": "<feedback on politeness>",
        "request_structure_feedback": "<feedback on request structure>",
        "specificity_feedback": "<feedback on specificity>",
        "solution_orientation_feedback": "<feedback on solution orientation>"
    }},
    "suggested_improvements": [
        "<specific improvement suggestion 1>",
        "<specific improvement suggestion 2>",
        "<specific improvement suggestion 3>"
    ],
    "encouragement": "<positive encouragement message>",
    "next_steps": "<what to focus on next>"
}}

Provide only the JSON output, no additional text.
"""
    
    try:
        print("🔄 [EVAL] Sending evaluation request to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert English language tutor specializing in B1 intermediate level problem-solving assessment."},
                {"role": "user", "content": prompt_template}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result_text = response.choices[0].message.content
        print(f"📊 [EVAL] Raw OpenAI response: {result_text[:200]}...")
        
        # Clean the response text to extract JSON
        result_text = result_text.strip()
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        print(f"📊 [EVAL] Cleaned response: {result_text[:200]}...")
        
        # Parse JSON response
        evaluation_result = json.loads(result_text)
        
        # Calculate success based on overall score (adjusted for B1 intermediate level)
        success = evaluation_result.get("overall_score", 0) >= 60
        
        print(f"✅ [EVAL] Evaluation completed. Score: {evaluation_result.get('overall_score', 0)}%")
        
        return {
            "success": success,
            "evaluation": evaluation_result,
            "suggested_improvement": evaluation_result.get("suggested_improvements", [""])[0] if evaluation_result.get("suggested_improvements") else "",
            "keyword_matches": evaluation_result.get("keyword_matches", []),
            "total_keywords": evaluation_result.get("total_keywords", 0),
            "matched_keywords_count": evaluation_result.get("matched_keywords_count", 0),
            "fluency_score": evaluation_result.get("clarity_score", 0) + evaluation_result.get("politeness_score", 0),
            "grammar_score": evaluation_result.get("request_structure_score", 0) + evaluation_result.get("specificity_score", 0) + evaluation_result.get("solution_orientation_score", 0),
            "response_type": evaluation_result.get("response_type_detected", ""),
            "score": evaluation_result.get("overall_score", 0),
            "is_correct": success,
            "completed": success
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ [EVAL] JSON parsing error: {str(e)}")
        print(f"📊 [EVAL] Failed to parse response: {result_text}")
        fallback_evaluation = {
            "overall_score": 50,
            "clarity_score": 10,
            "politeness_score": 12,
            "request_structure_score": 10,
            "specificity_score": 8,
            "solution_orientation_score": 10,
            "keyword_matches": [],
            "total_keywords": len(expected_keywords),
            "matched_keywords_count": 0,
            "response_type_detected": "unknown",
            "detailed_feedback": {
                "clarity_feedback": "Response was received but could not be fully evaluated.",
                "politeness_feedback": "Please try to use polite phrases and respectful tone.",
                "request_structure_feedback": "Make sure to ask for help clearly and appropriately.",
                "specificity_feedback": "Provide specific details about your problem.",
                "solution_orientation_feedback": "Ask for specific solutions or next steps."
            },
            "suggested_improvements": [
                "Try to be more specific in your response",
                "Use polite phrases when asking for help",
                "Practice clear problem description"
            ],
            "encouragement": "Good effort! Keep practicing to improve your problem-solving skills.",
            "next_steps": "Focus on using appropriate polite language for problem-solving."
        }
        
        return {
            "success": False,
            "error": "Failed to parse evaluation response",
            "suggested_improvement": "Please try again with a clearer response.",
            "evaluation": fallback_evaluation,
            "score": 50,
            "is_correct": False,
            "completed": False,
            "keyword_matches": [],
            "total_keywords": len(expected_keywords),
            "matched_keywords_count": 0,
            "fluency_score": 22,
            "grammar_score": 28,
            "response_type": "unknown"
        }
    except Exception as e:
        print(f"❌ [EVAL] OpenAI API error: {str(e)}")
        fallback_evaluation = {
            "overall_score": 50,
            "clarity_score": 10,
            "politeness_score": 12,
            "request_structure_score": 10,
            "specificity_score": 8,
            "solution_orientation_score": 10,
            "keyword_matches": [],
            "total_keywords": len(expected_keywords),
            "matched_keywords_count": 0,
            "response_type_detected": "unknown",
            "detailed_feedback": {
                "clarity_feedback": "Response was received but could not be fully evaluated.",
                "politeness_feedback": "Please try to use polite phrases and respectful tone.",
                "request_structure_feedback": "Make sure to ask for help clearly and appropriately.",
                "specificity_feedback": "Provide specific details about your problem.",
                "solution_orientation_feedback": "Ask for specific solutions or next steps."
            },
            "suggested_improvements": [
                "Try to be more specific in your response",
                "Use polite phrases when asking for help",
                "Practice clear problem description"
            ],
            "encouragement": "Good effort! Keep practicing to improve your problem-solving skills.",
            "next_steps": "Focus on using appropriate polite language for problem-solving."
        }
        
        return {
            "success": False,
            "error": f"Evaluation service error: {str(e)}",
            "suggested_improvement": "Please try again later.",
            "evaluation": fallback_evaluation,
            "score": 50,
            "is_correct": False,
            "completed": False,
            "keyword_matches": [],
            "total_keywords": len(expected_keywords),
            "matched_keywords_count": 0,
            "fluency_score": 22,
            "grammar_score": 28,
            "response_type": "unknown"
        }


def evaluate_response_ex1_stage4(user_response: str, topic: str, key_connectors: list, vocabulary_focus: list, model_response: str) -> dict:
    """
    Evaluate Stage 4 Exercise 1 (Abstract Topic Monologue) responses using OpenAI GPT-4o.
    
    This function evaluates B2 Upper Intermediate level abstract topic monologues based on:
    - Opinion clarity and balanced viewpoints
    - Effective use of transitional phrases and connectors
    - Fluency in extended monologue speaking
    - Grammar accuracy and lexical richness
    - Coherence and logical structure
    
    Args:
        user_response (str): The user's recorded monologue response
        topic (str): The abstract topic they were asked to speak about
        key_connectors (list): Expected transitional phrases and connectors
        vocabulary_focus (list): Domain-specific vocabulary to evaluate
        model_response (str): Example of a well-structured response for comparison
    
    Returns:
        dict: Comprehensive evaluation results with scores and detailed feedback
    """
    print(f"🔍 [EVAL] Evaluating Stage 4 Exercise 1 response: {user_response[:100]}...")
    
    try:
        # Create comprehensive evaluation prompt for B2 level abstract topic monologue
        evaluation_prompt = f"""
You are an expert English language assessor evaluating a B2 Upper Intermediate level abstract topic monologue. 

TOPIC: "{topic}"

USER RESPONSE: "{user_response}"

EXPECTED CONNECTORS: {key_connectors}
EXPECTED VOCABULARY: {vocabulary_focus}
MODEL RESPONSE EXAMPLE: "{model_response}"

Evaluate the response based on B2 Upper Intermediate criteria:

1. OPINION CLARITY (20 points):
   - Clear position statement
   - Balanced view with multiple perspectives
   - Personal insight and nuanced thinking

2. CONNECTOR USAGE (20 points):
   - Effective use of transitional phrases: {key_connectors}
   - Logical flow between ideas
   - Appropriate discourse markers

3. FLUENCY INDICATORS (20 points):
   - Smooth transitions and natural flow
   - Appropriate pacing for 60-90 second monologue
   - Minimal pauses and hesitations
   - Extended discourse fluency

4. GRAMMAR ACCURACY (20 points):
   - Complex sentence structures
   - Conditional forms and modals
   - Passive voice usage
   - B2 level grammatical complexity

5. LEXICAL RICHNESS (20 points):
   - Academic and domain-specific vocabulary
   - Synonyms and lexical variety
   - Collocations and idiomatic expressions
   - Sophisticated word choice

6. COHERENCE & STRUCTURE:
   - Logical organization of ideas
   - Supporting arguments and counter-arguments
   - Strong conclusion
   - Clear topic development

Provide your evaluation in the following JSON format:

{{
    "overall_score": <0-100>,
    "opinion_clarity_score": <0-20>,
    "connector_usage_score": <0-20>,
    "fluency_score": <0-20>,
    "grammar_score": <0-20>,
    "lexical_richness_score": <0-20>,
    "connector_matches": ["list", "of", "used", "connectors"],
    "vocabulary_matches": ["list", "of", "used", "vocabulary"],
    "total_connectors": <number>,
    "matched_connectors_count": <number>,
    "total_vocabulary": <number>,
    "matched_vocabulary_count": <number>,
    "response_type_detected": "opinion_essay|balanced_argument|personal_reflection",
    "detailed_feedback": {{
        "opinion_clarity_feedback": "Detailed feedback on opinion expression",
        "connector_feedback": "Feedback on transitional phrase usage",
        "fluency_feedback": "Feedback on speaking fluency and flow",
        "grammar_feedback": "Feedback on grammatical accuracy",
        "lexical_feedback": "Feedback on vocabulary usage and richness",
        "structure_feedback": "Feedback on overall organization and coherence"
    }},
    "suggested_improvements": [
        "Specific improvement suggestion 1",
        "Specific improvement suggestion 2",
        "Specific improvement suggestion 3"
    ],
    "encouragement": "Motivational message for the learner",
    "next_steps": "Recommended focus areas for improvement"
}}

Scoring Guidelines:
- 80-100: Excellent B2 level performance
- 70-79: Good B2 level with minor areas for improvement
- 60-69: Adequate B2 level with clear improvement areas
- Below 60: Needs more practice to reach B2 level

Focus on B2 Upper Intermediate standards for abstract topic discussion and extended monologue speaking.
"""

        print(f"🔄 [EVAL] Sending evaluation request to OpenAI...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert English language assessor specializing in B2 Upper Intermediate level evaluation. Provide detailed, constructive feedback in JSON format."
                },
                {
                    "role": "user",
                    "content": evaluation_prompt
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        result_text = response.choices[0].message.content
        print(f"📊 [EVAL] Raw OpenAI response: {result_text[:200]}...")
        
        # Clean the response text to extract JSON
        result_text = result_text.strip()
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        print(f"📊 [EVAL] Cleaned response: {result_text[:200]}...")
        
        # Parse JSON response
        evaluation_result = json.loads(result_text)
        
        # Calculate success based on overall score (B2 level requires 80%+)
        success = evaluation_result.get("overall_score", 0) >= 80
        
        print(f"✅ [EVAL] Evaluation completed. Score: {evaluation_result.get('overall_score', 0)}%")
        
        return {
            "success": success,
            "evaluation": evaluation_result,
            "suggested_improvement": evaluation_result.get("suggested_improvements", [""])[0] if evaluation_result.get("suggested_improvements") else "",
            "connector_matches": evaluation_result.get("connector_matches", []),
            "total_connectors": evaluation_result.get("total_connectors", len(key_connectors)),
            "matched_connectors_count": evaluation_result.get("matched_connectors_count", 0),
            "vocabulary_matches": evaluation_result.get("vocabulary_matches", []),
            "total_vocabulary": evaluation_result.get("total_vocabulary", len(vocabulary_focus)),
            "matched_vocabulary_count": evaluation_result.get("matched_vocabulary_count", 0),
            "fluency_score": evaluation_result.get("fluency_score", 0),
            "grammar_score": evaluation_result.get("grammar_score", 0),
            "lexical_richness_score": evaluation_result.get("lexical_richness_score", 0),
            "opinion_clarity_score": evaluation_result.get("opinion_clarity_score", 0),
            "connector_usage_score": evaluation_result.get("connector_usage_score", 0),
            "response_type": evaluation_result.get("response_type_detected", ""),
            "score": evaluation_result.get("overall_score", 0),
            "is_correct": success,
            "completed": success
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ [EVAL] JSON parsing error: {str(e)}")
        print(f"📊 [EVAL] Failed to parse response: {result_text}")
        fallback_evaluation = {
            "overall_score": 60,
            "opinion_clarity_score": 12,
            "connector_usage_score": 12,
            "fluency_score": 12,
            "grammar_score": 12,
            "lexical_richness_score": 12,
            "connector_matches": [],
            "vocabulary_matches": [],
            "total_connectors": len(key_connectors),
            "matched_connectors_count": 0,
            "total_vocabulary": len(vocabulary_focus),
            "matched_vocabulary_count": 0,
            "response_type_detected": "unknown",
            "detailed_feedback": {
                "opinion_clarity_feedback": "Response was received but could not be fully evaluated.",
                "connector_feedback": "Please try to use transitional phrases effectively.",
                "fluency_feedback": "Focus on speaking smoothly and naturally.",
                "grammar_feedback": "Pay attention to grammatical accuracy.",
                "lexical_feedback": "Use a variety of vocabulary and expressions.",
                "structure_feedback": "Organize your thoughts logically."
            },
            "suggested_improvements": [
                "Practice using transitional phrases like 'however', 'although', 'furthermore'",
                "Work on expressing balanced opinions with supporting arguments",
                "Focus on speaking fluently for extended periods"
            ],
            "encouragement": "Good effort! Keep practicing to improve your abstract topic discussion skills.",
            "next_steps": "Focus on using connectors and expressing complex opinions clearly."
        }
        
        return {
            "success": False,
            "error": "Failed to parse evaluation response",
            "suggested_improvement": "Please try again with a clearer response.",
            "evaluation": fallback_evaluation,
            "score": 60,
            "is_correct": False,
            "completed": False,
            "connector_matches": [],
            "total_connectors": len(key_connectors),
            "matched_connectors_count": 0,
            "vocabulary_matches": [],
            "total_vocabulary": len(vocabulary_focus),
            "matched_vocabulary_count": 0,
            "fluency_score": 12,
            "grammar_score": 12,
            "lexical_richness_score": 12,
            "opinion_clarity_score": 12,
            "connector_usage_score": 12,
            "response_type": "unknown"
        }
    except Exception as e:
        print(f"❌ [EVAL] OpenAI API error: {str(e)}")
        fallback_evaluation = {
            "overall_score": 60,
            "opinion_clarity_score": 12,
            "connector_usage_score": 12,
            "fluency_score": 12,
            "grammar_score": 12,
            "lexical_richness_score": 12,
            "connector_matches": [],
            "vocabulary_matches": [],
            "total_connectors": len(key_connectors),
            "matched_connectors_count": 0,
            "total_vocabulary": len(vocabulary_focus),
            "matched_vocabulary_count": 0,
            "response_type_detected": "unknown",
            "detailed_feedback": {
                "opinion_clarity_feedback": "Response was received but could not be fully evaluated.",
                "connector_feedback": "Please try to use transitional phrases effectively.",
                "fluency_feedback": "Focus on speaking smoothly and naturally.",
                "grammar_feedback": "Pay attention to grammatical accuracy.",
                "lexical_feedback": "Use a variety of vocabulary and expressions.",
                "structure_feedback": "Organize your thoughts logically."
            },
            "suggested_improvements": [
                "Practice using transitional phrases like 'however', 'although', 'furthermore'",
                "Work on expressing balanced opinions with supporting arguments",
                "Focus on speaking fluently for extended periods"
            ],
            "encouragement": "Good effort! Keep practicing to improve your abstract topic discussion skills.",
            "next_steps": "Focus on using connectors and expressing complex opinions clearly."
        }
        
        return {
            "success": False,
            "error": f"Evaluation service error: {str(e)}",
            "suggested_improvement": "Please try again later.",
            "evaluation": fallback_evaluation,
            "score": 60,
            "is_correct": False,
            "completed": False,
            "connector_matches": [],
            "total_connectors": len(key_connectors),
            "matched_connectors_count": 0,
            "vocabulary_matches": [],
            "total_vocabulary": len(vocabulary_focus),
            "matched_vocabulary_count": 0,
            "fluency_score": 12,
            "grammar_score": 12,
            "lexical_richness_score": 12,
            "opinion_clarity_score": 12,
            "connector_usage_score": 12,
            "response_type": "unknown"
        }




def evaluate_response_ex2_stage4(user_response: str, question: str, expected_keywords: list, vocabulary_focus: list, model_response: str) -> dict:
    """
    Evaluate Stage 4 Exercise 2 (Mock Interview Practice) responses using OpenAI GPT-4o.
    
    This function evaluates B2 Upper Intermediate level interview responses based on:
    - Answer relevance and depth
    - Professional confidence and tone
    - Grammar accuracy and fluency
    - Interview-specific vocabulary usage
    - Structured response organization
    
    Args:
        user_response (str): The user's recorded interview response
        question (str): The interview question they were asked
        expected_keywords (list): Expected keywords to include in response
        vocabulary_focus (list): Professional interview vocabulary to evaluate
        model_response (str): Example of a well-structured interview response
    
    Returns:
        dict: Comprehensive evaluation results with scores and detailed feedback
    """
    print(f"🔍 [EVAL] Evaluating Stage 4 Exercise 2 response: {user_response[:100]}...")
    
    try:
        # Create comprehensive evaluation prompt for B2 level interview practice
        evaluation_prompt = f"""
You are an expert English language assessor evaluating a B2 Upper Intermediate level mock interview response. 

INTERVIEW QUESTION: "{question}"

USER RESPONSE: "{user_response}"

EXPECTED KEYWORDS: {expected_keywords}
EXPECTED VOCABULARY: {vocabulary_focus}
MODEL RESPONSE EXAMPLE: "{model_response}"

Evaluate the response based on B2 Upper Intermediate interview criteria:

1. ANSWER RELEVANCE (25 points):
   - Directly addresses the interview question
   - Provides comprehensive and detailed response
   - Shows understanding of what the interviewer is asking
   - Demonstrates preparation and thoughtfulness

2. PROFESSIONAL CONFIDENCE (25 points):
   - Confident and self-assured tone
   - Professional demeanor and presentation
   - Clear and articulate expression
   - Appropriate level of enthusiasm and engagement

3. GRAMMAR & FLUENCY (25 points):
   - Grammatically accurate sentences
   - Natural flow and rhythm of speech
   - Appropriate use of complex sentence structures
   - Minimal hesitations and fillers

4. INTERVIEW VOCABULARY (25 points):
   - Use of professional interview language
   - Appropriate industry-specific terminology
   - Sophisticated vocabulary choices
   - Effective use of expected keywords: {expected_keywords}

5. STRUCTURE & ORGANIZATION:
   - Clear beginning, middle, and end
   - Logical progression of ideas
   - Appropriate use of transitions
   - Strong conclusion and call-to-action

Provide your evaluation in the following JSON format:

{{
    "overall_score": <0-100>,
    "answer_relevance_score": <0-25>,
    "confidence_tone_score": <0-25>,
    "grammar_fluency_score": <0-25>,
    "interview_vocabulary_score": <0-25>,
    "keyword_matches": ["list", "of", "used", "keywords"],
    "vocabulary_matches": ["list", "of", "used", "vocabulary"],
    "total_keywords": <number>,
    "matched_keywords_count": <number>,
    "total_vocabulary": <number>,
    "matched_vocabulary_count": <number>,
    "response_type_detected": "self_introduction|motivation|strengths_weaknesses|problem_solving|career_planning",
    "detailed_feedback": {{
        "relevance_feedback": "Detailed feedback on question relevance",
        "confidence_feedback": "Feedback on professional tone and confidence",
        "grammar_feedback": "Feedback on grammatical accuracy and fluency",
        "vocabulary_feedback": "Feedback on interview vocabulary usage",
        "structure_feedback": "Feedback on response organization and flow"
    }},
    "suggested_improvements": [
        "Specific improvement suggestion 1",
        "Specific improvement suggestion 2",
        "Specific improvement suggestion 3"
    ],
    "encouragement": "Motivational message for the learner",
    "next_steps": "Recommended focus areas for improvement"
}}

Scoring Guidelines:
- 80-100: Excellent B2 level interview performance
- 70-79: Good B2 level with minor areas for improvement
- 60-69: Adequate B2 level with clear improvement areas
- Below 60: Needs more practice to reach B2 level

Focus on B2 Upper Intermediate standards for professional interview communication and self-presentation.
"""

        print(f"🔄 [EVAL] Sending evaluation request to OpenAI...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert English language assessor specializing in B2 Upper Intermediate level interview evaluation. Provide detailed, constructive feedback in JSON format."
                },
                {
                    "role": "user",
                    "content": evaluation_prompt
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        result_text = response.choices[0].message.content
        print(f"📊 [EVAL] Raw OpenAI response: {result_text[:200]}...")
        
        # Clean the response text to extract JSON
        result_text = result_text.strip()
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        print(f"📊 [EVAL] Cleaned response: {result_text[:200]}...")
        
        # Parse JSON response
        evaluation_result = json.loads(result_text)
        
        # Calculate success based on overall score (B2 level requires 80%+)
        success = evaluation_result.get("overall_score", 0) >= 80
        
        print(f"✅ [EVAL] Evaluation completed. Score: {evaluation_result.get('overall_score', 0)}%")
        
        return {
            "success": success,
            "evaluation": evaluation_result,
            "suggested_improvement": evaluation_result.get("suggested_improvements", [""])[0] if evaluation_result.get("suggested_improvements") else "",
            "keyword_matches": evaluation_result.get("keyword_matches", []),
            "total_keywords": evaluation_result.get("total_keywords", len(expected_keywords)),
            "matched_keywords_count": evaluation_result.get("matched_keywords_count", 0),
            "vocabulary_matches": evaluation_result.get("vocabulary_matches", []),
            "total_vocabulary": evaluation_result.get("total_vocabulary", len(vocabulary_focus)),
            "matched_vocabulary_count": evaluation_result.get("matched_vocabulary_count", 0),
            "fluency_score": evaluation_result.get("grammar_fluency_score", 0),
            "grammar_score": evaluation_result.get("grammar_fluency_score", 0),
            "answer_relevance_score": evaluation_result.get("answer_relevance_score", 0),
            "confidence_tone_score": evaluation_result.get("confidence_tone_score", 0),
            "interview_vocabulary_score": evaluation_result.get("interview_vocabulary_score", 0),
            "response_type": evaluation_result.get("response_type_detected", ""),
            "score": evaluation_result.get("overall_score", 0),
            "is_correct": success,
            "completed": success
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ [EVAL] JSON parsing error: {str(e)}")
        print(f"📊 [EVAL] Failed to parse response: {result_text}")
        fallback_evaluation = {
            "overall_score": 60,
            "answer_relevance_score": 15,
            "confidence_tone_score": 15,
            "grammar_fluency_score": 15,
            "interview_vocabulary_score": 15,
            "keyword_matches": [],
            "vocabulary_matches": [],
            "total_keywords": len(expected_keywords),
            "matched_keywords_count": 0,
            "total_vocabulary": len(vocabulary_focus),
            "matched_vocabulary_count": 0,
            "response_type_detected": "unknown",
            "detailed_feedback": {
                "relevance_feedback": "Response was received but could not be fully evaluated.",
                "confidence_feedback": "Please try to maintain a confident and professional tone.",
                "grammar_feedback": "Focus on grammatical accuracy and fluency.",
                "vocabulary_feedback": "Use professional interview vocabulary and expected keywords.",
                "structure_feedback": "Organize your response with clear structure and flow."
            },
            "suggested_improvements": [
                "Practice using professional interview vocabulary",
                "Work on maintaining confident and clear communication",
                "Focus on directly addressing the interview question"
            ],
            "encouragement": "Good effort! Keep practicing to improve your interview skills.",
            "next_steps": "Focus on professional vocabulary and confident self-presentation."
        }
        
        return {
            "success": False,
            "error": "Failed to parse evaluation response",
            "suggested_improvement": "Please try again with a clearer response.",
            "evaluation": fallback_evaluation,
            "score": 60,
            "is_correct": False,
            "completed": False,
            "keyword_matches": [],
            "total_keywords": len(expected_keywords),
            "matched_keywords_count": 0,
            "vocabulary_matches": [],
            "total_vocabulary": len(vocabulary_focus),
            "matched_vocabulary_count": 0,
            "fluency_score": 15,
            "grammar_score": 15,
            "answer_relevance_score": 15,
            "confidence_tone_score": 15,
            "interview_vocabulary_score": 15,
            "response_type": "unknown"
        }
    except Exception as e:
        print(f"❌ [EVAL] OpenAI API error: {str(e)}")
        fallback_evaluation = {
            "overall_score": 60,
            "answer_relevance_score": 15,
            "confidence_tone_score": 15,
            "grammar_fluency_score": 15,
            "interview_vocabulary_score": 15,
            "keyword_matches": [],
            "vocabulary_matches": [],
            "total_keywords": len(expected_keywords),
            "matched_keywords_count": 0,
            "total_vocabulary": len(vocabulary_focus),
            "matched_vocabulary_count": 0,
            "response_type_detected": "unknown",
            "detailed_feedback": {
                "relevance_feedback": "Response was received but could not be fully evaluated.",
                "confidence_feedback": "Please try to maintain a confident and professional tone.",
                "grammar_feedback": "Focus on grammatical accuracy and fluency.",
                "vocabulary_feedback": "Use professional interview vocabulary and expected keywords.",
                "structure_feedback": "Organize your response with clear structure and flow."
            },
            "suggested_improvements": [
                "Practice using professional interview vocabulary",
                "Work on maintaining confident and clear communication",
                "Focus on directly addressing the interview question"
            ],
            "encouragement": "Good effort! Keep practicing to improve your interview skills.",
            "next_steps": "Focus on professional vocabulary and confident self-presentation."
        }
        
        return {
            "success": False,
            "error": f"Evaluation service error: {str(e)}",
            "suggested_improvement": "Please try again later.",
            "evaluation": fallback_evaluation,
            "score": 60,
            "is_correct": False,
            "completed": False,
            "keyword_matches": [],
            "total_keywords": len(expected_keywords),
            "matched_keywords_count": 0,
            "vocabulary_matches": [],
            "total_vocabulary": len(vocabulary_focus),
            "matched_vocabulary_count": 0,
            "fluency_score": 15,
            "grammar_score": 15,
            "answer_relevance_score": 15,
            "confidence_tone_score": 15,
            "interview_vocabulary_score": 15,
            "response_type": "unknown"
        }



def evaluate_response_ex3_stage4(user_response: str, news_title: str, summary_text: str, expected_keywords: list, vocabulary_focus: list, model_summary: str) -> dict:
    """
    Evaluate user's news summary response for Stage 4 Exercise 3 (News Summary Challenge)
    
    Args:
        user_response: User's recorded summary
        news_title: Title of the news article
        summary_text: Original news text
        expected_keywords: List of expected keywords
        vocabulary_focus: List of vocabulary words to focus on
        model_summary: Example model summary
    
    Returns:
        Dictionary with evaluation results
    """
    try:
        print(f"🔍 [EVAL] Evaluating news summary response: {user_response[:50]}...")
        
        # Create comprehensive evaluation prompt
        prompt = f"""
You are an expert English language evaluator specializing in B2 Upper Intermediate level assessments. 
Evaluate the following news summary response based on the criteria below.

NEWS TITLE: {news_title}
ORIGINAL NEWS TEXT: {summary_text}
USER'S SUMMARY: {user_response}
MODEL SUMMARY: {model_summary}
EXPECTED KEYWORDS: {', '.join(expected_keywords)}
VOCABULARY FOCUS: {', '.join(vocabulary_focus)}

EVALUATION CRITERIA (Total: 100 points):
1. Main Points Coverage (30 points): Does the summary cover the key facts, events, and important details from the original news?
2. Grammar & Structure (25 points): Is the grammar correct and the structure clear and logical?
3. Paraphrasing Skills (25 points): Does the user paraphrase effectively without copying the original text?
4. Neutral Tone (20 points): Is the tone objective and journalistic, avoiding personal opinions?

Provide your evaluation in the following JSON format:
{{
    "overall_score": <0-100>,
    "main_points_coverage_score": <0-30>,
    "grammar_structure_score": <0-25>,
    "paraphrasing_skills_score": <0-25>,
    "neutral_tone_score": <0-20>,
    "keyword_matches": ["list", "of", "matched", "keywords"],
    "total_keywords": <total_number_of_expected_keywords>,
    "matched_keywords_count": <number_of_matched_keywords>,
    "summary_type_detected": "<summary/paraphrase/copy>",
    "detailed_feedback": {{
        "main_points_feedback": "<feedback on main points coverage>",
        "grammar_feedback": "<feedback on grammar and structure>",
        "paraphrasing_feedback": "<feedback on paraphrasing skills>",
        "tone_feedback": "<feedback on neutral tone>"
    }},
    "suggested_improvements": ["improvement1", "improvement2", "improvement3"],
    "encouragement": "<positive encouragement message>",
    "next_steps": "<specific next steps for improvement>"
}}

Focus on B2 Upper Intermediate level expectations. Be encouraging but honest in your assessment.
"""

        print("🔄 [EVAL] Sending evaluation request to OpenAI...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert English language evaluator for B2 Upper Intermediate level. Provide evaluations in the exact JSON format requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        print("📊 [EVAL] Raw OpenAI response received")
        
        # Extract and clean the response
        raw_response = response.choices[0].message.content.strip()
        print(f"📊 [EVAL] Raw response: {raw_response[:200]}...")
        
        # Clean the response to extract JSON
        cleaned_response = raw_response
        if "```json" in raw_response:
            cleaned_response = raw_response.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_response:
            cleaned_response = raw_response.split("```")[1].strip()
        
        print(f"📊 [EVAL] Cleaned response: {cleaned_response[:200]}...")
        
        # Parse JSON response
        evaluation_data = json.loads(cleaned_response)
        
        # Calculate overall score
        overall_score = evaluation_data.get("overall_score", 0)
        
        # Determine if the response meets the success threshold (80% for B2 level)
        success_threshold = 80
        is_successful = overall_score >= success_threshold
        
        # Count keyword matches
        keyword_matches = evaluation_data.get("keyword_matches", [])
        total_keywords = evaluation_data.get("total_keywords", len(expected_keywords))
        matched_count = evaluation_data.get("matched_keywords_count", len(keyword_matches))
        
        # Determine summary type
        summary_type = evaluation_data.get("summary_type_detected", "summary")
        
        # Calculate fluency and grammar scores (scaled down for consistency)
        fluency_score = min(50, evaluation_data.get("grammar_structure_score", 0) * 2)
        grammar_score = min(50, evaluation_data.get("grammar_structure_score", 0) * 2)
        
        print(f"✅ [EVAL] Evaluation completed. Score: {overall_score}%")
        
        return {
            "success": True,
            "news_title": news_title,
            "expected_keywords": expected_keywords,
            "user_text": user_response,
            "evaluation": evaluation_data,
            "suggested_improvement": evaluation_data.get("suggested_improvements", [""])[0] if evaluation_data.get("suggested_improvements") else "",
            "keyword_matches": keyword_matches,
            "total_keywords": total_keywords,
            "matched_keywords_count": matched_count,
            "fluency_score": fluency_score,
            "grammar_score": grammar_score,
            "summary_type": summary_type,
            "score": overall_score,
            "is_correct": is_successful,
            "completed": is_successful
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ [EVAL] JSON parsing error: {e}")
        return {
            "success": False,
            "error": "json_parsing_error",
            "message": "Failed to parse evaluation response"
        }
    except Exception as e:
        print(f"❌ [EVAL] Evaluation error: {e}")
        return {
            "success": False,
            "error": "evaluation_error",
            "message": f"Evaluation failed: {str(e)}"
        }


def evaluate_response_ex1_stage5(user_response: str, topic: str, ai_position: str, expected_keywords: list, vocabulary_focus: list, model_response: str) -> dict:
    """
    Evaluate critical thinking dialogue responses for Stage 5 Exercise 1.
    Focuses on argument structure, critical thinking, vocabulary range, fluency, and discourse markers.
    """
    print(f"🔍 [EVAL] Evaluating critical thinking response: {user_response[:50]}...")
    
    prompt = f"""
You are an expert English language evaluator specializing in C1 Advanced level critical thinking and philosophical discussions. Evaluate the user's response to a complex philosophical debate topic.

**Topic:** {topic}
**AI Position:** {ai_position}
**User Response:** {user_response}
**Expected Keywords:** {', '.join(expected_keywords)}
**Vocabulary Focus:** {', '.join(vocabulary_focus)}
**Model Response:** {model_response}

**Evaluation Criteria (Total: 100 points):**
1. **Argument Structure (25 points):** Logical organization, clear introduction, main arguments, counter-arguments, evidence, and conclusion
2. **Critical Thinking (25 points):** Depth of analysis, ability to consider multiple perspectives, evidence-based reasoning, and nuanced understanding
3. **Vocabulary Range (20 points):** Use of advanced academic vocabulary, sophisticated word choices, and appropriate terminology
4. **Fluency & Grammar (20 points):** Natural flow, grammatical accuracy, sentence variety, and coherence
5. **Discourse Markers (10 points):** Effective use of connectors, transition phrases, and logical flow indicators

**Scoring Guidelines:**
- **90-100:** Exceptional C1 level with sophisticated argumentation and vocabulary
- **80-89:** Strong C1 level with clear structure and advanced language use
- **70-79:** Good C1 level with some areas for improvement
- **60-69:** Adequate C1 level with noticeable gaps
- **Below 60:** Needs significant improvement to reach C1 level

**Success Threshold:** 80 points (C1 Advanced level)

**IMPORTANT:** Set "completed" and "is_correct" to true ONLY if the overall_score is 80 or higher.

Analyze the response and provide detailed feedback in the following JSON format:

{{
    "success": true/false,
    "overall_score": <0-100>,
    "argument_structure_score": <0-25>,
    "critical_thinking_score": <0-25>,
    "vocabulary_range_score": <0-20>,
    "fluency_grammar_score": <0-20>,
    "discourse_markers_score": <0-10>,
    "keyword_matches": ["list", "of", "matched", "keywords"],
    "total_keywords": <number>,
    "matched_keywords_count": <number>,
    "vocabulary_matches": ["list", "of", "matched", "vocabulary"],
    "total_vocabulary": <number>,
    "matched_vocabulary_count": <number>,
    "argument_type_detected": "balanced/one-sided/undeveloped",
    "detailed_feedback": {{
        "argument_structure_feedback": "<detailed feedback on argument organization>",
        "critical_thinking_feedback": "<detailed feedback on analysis depth>",
        "vocabulary_feedback": "<detailed feedback on word choice>",
        "fluency_feedback": "<detailed feedback on flow and grammar>",
        "discourse_feedback": "<detailed feedback on connectors>"
    }},
    "suggested_improvements": [
        "<specific improvement suggestion 1>",
        "<specific improvement suggestion 2>",
        "<specific improvement suggestion 3>"
    ],
    "encouragement": "<motivational message>",
    "next_steps": "<specific guidance for improvement>",
    "score": <0-100>
}}

Note: Do NOT include "completed" or "is_correct" fields in your response. These will be calculated automatically based on the score threshold.

Ensure the response is valid JSON and all scores are numerical values.
"""

    try:
        print("🔄 [EVAL] Sending evaluation request to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert English language evaluator for C1 Advanced level critical thinking exercises. Provide detailed, constructive feedback in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        print("📊 [EVAL] Raw OpenAI response received")
        raw_response = response.choices[0].message.content.strip()
        print(f"📊 [EVAL] Raw response: {raw_response[:200]}...")
        
        # Clean the response to ensure valid JSON
        cleaned_response = raw_response
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        print(f"📊 [EVAL] Cleaned response: {cleaned_response[:200]}...")
        
        evaluation = json.loads(cleaned_response)
        
        # Validate and set default values
        if not isinstance(evaluation.get("overall_score"), (int, float)):
            evaluation["overall_score"] = 0
        if not isinstance(evaluation.get("score"), (int, float)):
            evaluation["score"] = evaluation.get("overall_score", 0)
        
        # Force correct completion logic based on score threshold (80 for Stage 5)
        score = evaluation.get("score", 0)
        evaluation["completed"] = score >= 80
        evaluation["is_correct"] = score >= 80
            
        print(f"✅ [EVAL] Evaluation completed. Score: {evaluation.get('score', 0)}%")
        
        return {
            "success": True,
            "evaluation": evaluation,
            "suggested_improvement": evaluation.get("suggested_improvements", [""])[0] if evaluation.get("suggested_improvements") else "",
            "keyword_matches": evaluation.get("keyword_matches", []),
            "total_keywords": evaluation.get("total_keywords", 0),
            "matched_keywords_count": evaluation.get("matched_keywords_count", 0),
            "vocabulary_matches": evaluation.get("vocabulary_matches", []),
            "total_vocabulary": evaluation.get("total_vocabulary", 0),
            "matched_vocabulary_count": evaluation.get("matched_vocabulary_count", 0),
            "fluency_score": evaluation.get("fluency_grammar_score", 0),
            "grammar_score": evaluation.get("fluency_grammar_score", 0),
            "argument_type": evaluation.get("argument_type_detected", ""),
            "score": evaluation.get("score", 0),
            "is_correct": evaluation.get("is_correct", False),
            "completed": evaluation.get("completed", False)
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ [EVAL] JSON parsing error: {str(e)}")
        return {
            "success": False,
            "error": "evaluation_failed",
            "message": "Failed to parse evaluation response. Please try again.",
            "score": 0,
            "is_correct": False,
            "completed": False
        }
    except Exception as e:
        print(f"❌ [EVAL] Evaluation error: {str(e)}")
        return {
            "success": False,
            "error": "evaluation_failed",
            "message": "Failed to evaluate response. Please try again.",
            "score": 0,
            "is_correct": False,
            "completed": False
        }


def evaluate_response_ex2_stage5(user_response: str, topic: str, expected_keywords: list, vocabulary_focus: list, model_response: str, expected_structure: str) -> dict:
    """
    Evaluate Stage 5 Exercise 2 (Academic Presentation) responses.
    Focuses on academic presentation skills, argument structure, evidence usage, and formal tone.
    """
    print(f"🔄 [EVAL] Evaluating Stage 5 Exercise 2 (Academic Presentation)")
    print(f"📝 [EVAL] Topic: {topic}")
    print(f"📝 [EVAL] User response: {user_response[:100]}...")
    print(f"📝 [EVAL] Expected keywords: {expected_keywords}")
    print(f"📝 [EVAL] Expected structure: {expected_structure}")
    
    prompt = f"""
You are an expert English language evaluator for C1 Advanced level academic presentations. Evaluate the user's 3-minute academic presentation based on the following criteria:

**Topic:** {topic}
**User's Presentation:** {user_response}
**Expected Keywords:** {expected_keywords}
**Expected Structure:** {expected_structure}
**Vocabulary Focus:** {vocabulary_focus}
**Model Response:** {model_response}

**Evaluation Criteria (100 points total):**
1. **Argument Structure (25 points):** Introduction, thesis statement, supporting evidence, counter-arguments, conclusion
2. **Evidence Usage (25 points):** Use of examples, statistics, research, logical reasoning
3. **Academic Tone (20 points):** Formal language, professional vocabulary, appropriate register
4. **Fluency & Pacing (15 points):** Smooth delivery, appropriate speed, clear articulation
5. **Vocabulary Range (15 points):** Sophisticated word choice, academic terminology

**Analysis Tasks:**
1. **Keyword Analysis:** Check how many expected keywords were used appropriately
2. **Structure Analysis:** Evaluate if the presentation follows the expected academic structure
3. **Evidence Analysis:** Assess the quality and relevance of evidence provided
4. **Language Analysis:** Evaluate academic tone, vocabulary sophistication, and grammar
5. **Overall Assessment:** Provide a comprehensive score and detailed feedback

**Response Format (JSON only):**
{{
    "overall_score": <0-100>,
    "argument_structure_score": <0-25>,
    "evidence_usage_score": <0-25>,
    "academic_tone_score": <0-20>,
    "fluency_pacing_score": <0-15>,
    "vocabulary_range_score": <0-15>,
    "keyword_matches": {expected_keywords},
    "matched_keywords_count": <number of keywords used>,
    "total_keywords": {len(expected_keywords)},
    "vocabulary_matches": {vocabulary_focus},
    "matched_vocabulary_count": <number of vocabulary words used>,
    "total_vocabulary": {len(vocabulary_focus)},
    "structure_followed": <true/false>,
    "evidence_provided": <true/false>,
    "academic_tone_maintained": <true/false>,
    "detailed_feedback": {{
        "argument_structure_feedback": "<detailed feedback on structure>",
        "evidence_usage_feedback": "<detailed feedback on evidence>",
        "academic_tone_feedback": "<detailed feedback on tone>",
        "fluency_feedback": "<detailed feedback on delivery>",
        "vocabulary_feedback": "<detailed feedback on word choice>"
    }},
    "suggested_improvements": [
        "<specific improvement suggestion 1>",
        "<specific improvement suggestion 2>",
        "<specific improvement suggestion 3>"
    ],
    "encouragement": "<motivational message>",
    "next_steps": "<specific guidance for improvement>",
    "score": <0-100>
}}

Note: Do NOT include "completed" or "is_correct" fields in your response. These will be calculated automatically based on the score threshold.

Ensure the response is valid JSON and all scores are numerical values.
"""

    try:
        print("🔄 [EVAL] Sending evaluation request to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert English language evaluator for C1 Advanced level academic presentations. Provide detailed, constructive feedback in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        print("📊 [EVAL] Raw OpenAI response received")
        raw_response = response.choices[0].message.content.strip()
        print(f"📊 [EVAL] Raw response: {raw_response[:200]}...")
        
        # Clean the response to ensure valid JSON
        cleaned_response = raw_response
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        print(f"📊 [EVAL] Cleaned response: {cleaned_response[:200]}...")
        
        evaluation = json.loads(cleaned_response)
        
        # Validate and set default values
        if not isinstance(evaluation.get("overall_score"), (int, float)):
            evaluation["overall_score"] = 0
        if not isinstance(evaluation.get("score"), (int, float)):
            evaluation["score"] = evaluation.get("overall_score", 0)
        
        # Force correct completion logic based on score threshold (80 for Stage 5)
        score = evaluation.get("score", 0)
        evaluation["completed"] = score >= 80
        evaluation["is_correct"] = score >= 80
            
        print(f"✅ [EVAL] Evaluation completed. Score: {evaluation.get('score', 0)}%")
        
        return {
            "success": True,
            "evaluation": evaluation,
            "suggested_improvement": evaluation.get("suggested_improvements", [""])[0] if evaluation.get("suggested_improvements") else "",
            "keyword_matches": evaluation.get("keyword_matches", []),
            "total_keywords": evaluation.get("total_keywords", 0),
            "matched_keywords_count": evaluation.get("matched_keywords_count", 0),
            "vocabulary_matches": evaluation.get("vocabulary_matches", []),
            "total_vocabulary": evaluation.get("total_vocabulary", 0),
            "matched_vocabulary_count": evaluation.get("matched_vocabulary_count", 0),
            "fluency_score": evaluation.get("fluency_pacing_score", 0),
            "grammar_score": evaluation.get("academic_tone_score", 0),
            "argument_structure_score": evaluation.get("argument_structure_score", 0),
            "academic_tone_score": evaluation.get("academic_tone_score", 0),
            "evidence_usage_score": evaluation.get("evidence_usage_score", 0),
            "vocabulary_range_score": evaluation.get("vocabulary_range_score", 0),
            "structure_followed": evaluation.get("structure_followed", False),
            "evidence_provided": evaluation.get("evidence_provided", False),
            "academic_tone_maintained": evaluation.get("academic_tone_maintained", False),
            "score": evaluation.get("score", 0),
            "is_correct": evaluation.get("is_correct", False),
            "completed": evaluation.get("completed", False)
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ [EVAL] JSON parsing error: {str(e)}")
        return {
            "success": False,
            "error": "evaluation_failed",
            "message": "Failed to parse evaluation response. Please try again.",
            "score": 0,
            "is_correct": False,
            "completed": False
        }
    except Exception as e:
        print(f"❌ [EVAL] Evaluation error: {str(e)}")
        return {
            "success": False,
            "error": "evaluation_failed",
            "message": "Failed to evaluate response. Please try again.",
            "score": 0,
            "is_correct": False,
            "completed": False
        }



def evaluate_response_ex3_stage5(user_response: str, question: str, expected_keywords: list, vocabulary_focus: list, model_answer: str, expected_structure: str) -> dict:
    """
    Evaluate in-depth interview responses for Stage 5 Exercise 3.
    Focuses on professional communication, STAR method usage, vocabulary sophistication, and interview skills.
    """
    print(f"🔄 [EVAL] Evaluating Stage 5 Exercise 3 (In-Depth Interview)")
    print(f"📝 [EVAL] Question: {question}")
    print(f"📝 [EVAL] User response: {user_response[:100]}...")
    print(f"📝 [EVAL] Expected keywords: {expected_keywords}")
    print(f"📝 [EVAL] Expected structure: {expected_structure}")
    
    prompt = f"""
You are an expert English language evaluator for C1 Advanced level in-depth interview responses. Evaluate the user's response to a professional interview question based on the following criteria:

**Interview Question:** {question}
**User's Response:** {user_response}
**Expected Keywords:** {expected_keywords}
**Vocabulary Focus:** {vocabulary_focus}
**Expected Structure:** {expected_structure}
**Model Answer:** {model_answer}

**Evaluation Criteria (100 points total):**
1. **STAR Method Usage (25 points):** Situation, Task, Action, Result structure with clear examples
2. **Professional Communication (25 points):** Appropriate tone, confidence, clarity, and impact
3. **Vocabulary Sophistication (20 points):** Advanced professional vocabulary, industry terminology
4. **Fluency & Articulation (15 points):** Smooth delivery, clear pronunciation, natural flow
5. **Content Relevance (15 points):** Directly addresses the question with relevant examples

**Analysis Tasks:**
1. **STAR Analysis:** Check if the response follows Situation-Task-Action-Result structure
2. **Keyword Integration:** Assess how well expected keywords are naturally incorporated
3. **Professional Tone:** Evaluate appropriateness for interview context
4. **Vocabulary Assessment:** Check use of sophisticated professional language
5. **Overall Impact:** Assess the effectiveness of the response

**Response Format (JSON only):**
{{
    "overall_score": <0-100>,
    "star_method_score": <0-25>,
    "professional_communication_score": <0-25>,
    "vocabulary_sophistication_score": <0-20>,
    "fluency_articulation_score": <0-15>,
    "content_relevance_score": <0-15>,
    "keyword_matches": {expected_keywords},
    "matched_keywords_count": <number of keywords used>,
    "total_keywords": {len(expected_keywords)},
    "vocabulary_matches": {vocabulary_focus},
    "matched_vocabulary_count": <number of vocabulary words used>,
    "total_vocabulary": {len(vocabulary_focus)},
    "star_structure_followed": <true/false>,
    "professional_tone_maintained": <true/false>,
    "relevant_examples_provided": <true/false>,
    "detailed_feedback": {{
        "star_method_feedback": "<detailed feedback on STAR structure>",
        "professional_communication_feedback": "<detailed feedback on communication style>",
        "vocabulary_feedback": "<detailed feedback on word choice>",
        "fluency_feedback": "<detailed feedback on delivery>",
        "content_feedback": "<detailed feedback on relevance>"
    }},
    "suggested_improvements": [
        "<specific improvement suggestion 1>",
        "<specific improvement suggestion 2>",
        "<specific improvement suggestion 3>"
    ],
    "encouragement": "<motivational message>",
    "next_steps": "<specific guidance for improvement>",
    "score": <0-100>
}}

Note: Do NOT include "completed" or "is_correct" fields in your response. These will be calculated automatically based on the score threshold.

Ensure the response is valid JSON and all scores are numerical values.
"""

    try:
        print("🔄 [EVAL] Sending evaluation request to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert English language evaluator for C1 Advanced level in-depth interview responses. Provide detailed, constructive feedback in JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        print("📊 [EVAL] Raw OpenAI response received")
        raw_response = response.choices[0].message.content.strip()
        print(f"📊 [EVAL] Raw response: {raw_response[:200]}...")
        
        # Clean the response to ensure valid JSON
        cleaned_response = raw_response
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        print(f"📊 [EVAL] Cleaned response: {cleaned_response[:200]}...")
        
        evaluation = json.loads(cleaned_response)
        
        # Validate and set default values
        if not isinstance(evaluation.get("overall_score"), (int, float)):
            evaluation["overall_score"] = 0
        if not isinstance(evaluation.get("score"), (int, float)):
            evaluation["score"] = evaluation.get("overall_score", 0)
        
        # Force correct completion logic based on score threshold (80 for Stage 5)
        score = evaluation.get("score", 0)
        evaluation["completed"] = score >= 70
        evaluation["is_correct"] = score >= 70
            
        print(f"✅ [EVAL] Evaluation completed. Score: {evaluation.get('score', 0)}%")
        
        return {
            "success": True,
            "evaluation": evaluation,
            "suggested_improvement": evaluation.get("suggested_improvements", [""])[0] if evaluation.get("suggested_improvements") else "",
            "keyword_matches": evaluation.get("keyword_matches", []),
            "total_keywords": evaluation.get("total_keywords", 0),
            "matched_keywords_count": evaluation.get("matched_keywords_count", 0),
            "vocabulary_matches": evaluation.get("vocabulary_matches", []),
            "total_vocabulary": evaluation.get("total_vocabulary", 0),
            "matched_vocabulary_count": evaluation.get("matched_vocabulary_count", 0),
            "fluency_score": evaluation.get("fluency_articulation_score", 0),
            "grammar_score": evaluation.get("professional_communication_score", 0),
            "star_method_score": evaluation.get("star_method_score", 0),
            "professional_communication_score": evaluation.get("professional_communication_score", 0),
            "vocabulary_sophistication_score": evaluation.get("vocabulary_sophistication_score", 0),
            "content_relevance_score": evaluation.get("content_relevance_score", 0),
            "star_structure_followed": evaluation.get("star_structure_followed", False),
            "professional_tone_maintained": evaluation.get("professional_tone_maintained", False),
            "relevant_examples_provided": evaluation.get("relevant_examples_provided", False),
            "score": evaluation.get("score", 0),
            "is_correct": evaluation.get("is_correct", False),
            "completed": evaluation.get("completed", False)
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ [EVAL] JSON parsing error: {str(e)}")
        return {
            "success": False,
            "error": "evaluation_failed",
            "message": "Failed to parse evaluation response. Please try again.",
            "score": 0,
            "is_correct": False,
            "completed": False
        }
    except Exception as e:
        print(f"❌ [EVAL] Evaluation error: {str(e)}")
        return {
            "success": False,
            "error": "evaluation_failed",
            "message": "Failed to evaluate response. Please try again.",
            "score": 0,
            "is_correct": False,
            "completed": False
        }

def evaluate_response_ex1_stage6(expected_keywords, user_text, topic_text, model_response, evaluation_criteria):
    """
    Evaluate Stage 6 Exercise 1 (AI-Guided Spontaneous Speech) responses using ChatGPT.
    
    Args:
        expected_keywords: List of expected keywords from the topic
        user_text: Transcribed user response
        topic_text: The spontaneous speech topic
        model_response: Expected model response for comparison
        evaluation_criteria: Dictionary with evaluation weights
    
    Returns:
        Dictionary with evaluation results
    """
    try:
        print(f"🔄 [EVAL] Starting Stage 6 Exercise 1 evaluation")
        print(f"📝 [EVAL] Topic: {topic_text}")
        print(f"🎤 [EVAL] User response: {user_text}")
        print(f"🔑 [EVAL] Expected keywords: {expected_keywords}")
        
        # Extract evaluation criteria weights
        spontaneous_fluency_weight = evaluation_criteria.get("spontaneous_fluency", 30)
        depth_of_thought_weight = evaluation_criteria.get("depth_of_thought", 25)
        advanced_vocabulary_weight = evaluation_criteria.get("advanced_vocabulary", 25)
        structural_coherence_weight = evaluation_criteria.get("structural_coherence", 20)
        
        # Create sophisticated evaluation prompt
        evaluation_prompt = f"""
You are an expert English language evaluator for C2-level spontaneous speech exercises. Evaluate the following response based on the given criteria.

TOPIC: {topic_text}

USER RESPONSE: {user_text}

EXPECTED KEYWORDS: {', '.join(expected_keywords)}

MODEL RESPONSE (for reference): {model_response}

EVALUATION CRITERIA:
1. Spontaneous Fluency (Weight: {spontaneous_fluency_weight}%): Natural flow, minimal hesitation, confident delivery
2. Depth of Thought (Weight: {depth_of_thought_weight}%): Sophisticated analysis, nuanced perspectives, intellectual depth
3. Advanced Vocabulary (Weight: {advanced_vocabulary_weight}%): C2-level terminology, precise word choice, academic language
4. Structural Coherence (Weight: {structural_coherence_weight}%): Logical organization, clear progression, well-structured arguments

Please provide a comprehensive evaluation in the following JSON format:

{{
    "overall_score": <0-100>,
    "spontaneous_fluency_score": <0-100>,
    "depth_of_thought_score": <0-100>,
    "advanced_vocabulary_score": <0-100>,
    "structural_coherence_score": <0-100>,
    "keyword_matches": <number of keywords used>,
    "total_keywords": <total number of expected keywords>,
    "fluency_analysis": "<detailed analysis of spontaneous fluency>",
    "thought_analysis": "<detailed analysis of depth of thought>",
    "vocabulary_analysis": "<detailed analysis of vocabulary usage>",
    "coherence_analysis": "<detailed analysis of structural coherence>",
    "strengths": ["<list of key strengths>"],
    "areas_for_improvement": ["<list of specific improvement areas>"],
    "suggested_improvement": "<comprehensive improvement suggestion>",
    "is_correct": <true/false based on overall quality>,
    "completed": <true if score >= 80, false otherwise>
}}

Focus on C2-level expectations: sophisticated language, complex ideas, nuanced arguments, and native-like fluency.
"""

        print(f"🔄 [EVAL] Sending evaluation request to ChatGPT")
        
        # Get ChatGPT response
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert English language evaluator for C2-level spontaneous speech exercises. Provide detailed, professional evaluations in the exact JSON format requested."},
                {"role": "user", "content": evaluation_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        # Extract and parse the response
        evaluation_text = response.choices[0].message.content.strip()
        print(f"📊 [EVAL] ChatGPT response received: {evaluation_text[:200]}...")
        
        # Parse JSON response
        try:
            evaluation_data = json.loads(evaluation_text)
            print(f"✅ [EVAL] JSON parsed successfully")
        except json.JSONDecodeError as e:
            print(f"❌ [EVAL] JSON parsing error: {str(e)}")
            # Fallback evaluation
            return create_fallback_evaluation(user_text, expected_keywords, topic_text)
        
        # Validate and process the evaluation data
        overall_score = evaluation_data.get("overall_score", 0)
        spontaneous_fluency_score = evaluation_data.get("spontaneous_fluency_score", 0)
        depth_of_thought_score = evaluation_data.get("depth_of_thought_score", 0)
        advanced_vocabulary_score = evaluation_data.get("advanced_vocabulary_score", 0)
        structural_coherence_score = evaluation_data.get("structural_coherence_score", 0)
        keyword_matches = evaluation_data.get("keyword_matches", 0)
        total_keywords = evaluation_data.get("total_keywords", len(expected_keywords))
        
        # Calculate weighted score
        weighted_score = (
            (spontaneous_fluency_score * spontaneous_fluency_weight / 100) +
            (depth_of_thought_score * depth_of_thought_weight / 100) +
            (advanced_vocabulary_score * advanced_vocabulary_weight / 100) +
            (structural_coherence_score * structural_coherence_weight / 100)
        )
        
        # Determine completion status
        is_correct = weighted_score >= 70
        completed = weighted_score >= 80
        
        print(f"📊 [EVAL] Evaluation results:")
        print(f"   Overall Score: {weighted_score:.1f}")
        print(f"   Spontaneous Fluency: {spontaneous_fluency_score}")
        print(f"   Depth of Thought: {depth_of_thought_score}")
        print(f"   Advanced Vocabulary: {advanced_vocabulary_score}")
        print(f"   Structural Coherence: {structural_coherence_score}")
        print(f"   Keyword Matches: {keyword_matches}/{total_keywords}")
        print(f"   Completed: {completed}")
        
        return {
            "score": round(weighted_score, 1),
            "spontaneous_fluency_score": spontaneous_fluency_score,
            "depth_of_thought_score": depth_of_thought_score,
            "advanced_vocabulary_score": advanced_vocabulary_score,
            "structural_coherence_score": structural_coherence_score,
            "keyword_matches": keyword_matches,
            "total_keywords": total_keywords,
            "fluency_score": spontaneous_fluency_score,  # For compatibility
            "grammar_score": structural_coherence_score,  # For compatibility
            "is_correct": is_correct,
            "completed": completed,
            "suggested_improvement": evaluation_data.get("suggested_improvement", ""),
            "strengths": evaluation_data.get("strengths", []),
            "areas_for_improvement": evaluation_data.get("areas_for_improvement", []),
            "fluency_analysis": evaluation_data.get("fluency_analysis", ""),
            "thought_analysis": evaluation_data.get("thought_analysis", ""),
            "vocabulary_analysis": evaluation_data.get("vocabulary_analysis", ""),
            "coherence_analysis": evaluation_data.get("coherence_analysis", "")
        }
        
    except Exception as e:
        print(f"❌ [EVAL] Error in Stage 6 Exercise 1 evaluation: {str(e)}")
        return create_fallback_evaluation(user_text, expected_keywords, topic_text)

def create_fallback_evaluation(user_text, expected_keywords, topic_text):
    """Create a fallback evaluation when ChatGPT fails"""
    print(f"🔄 [EVAL] Creating fallback evaluation")
    
    # Simple keyword matching
    user_words = set(user_text.lower().split())
    keyword_matches = sum(1 for keyword in expected_keywords if keyword.lower() in user_words)
    total_keywords = len(expected_keywords)
    
    # Basic scoring
    keyword_score = (keyword_matches / total_keywords) * 100 if total_keywords > 0 else 0
    length_score = min(len(user_text.split()) / 50 * 100, 100)  # Target: 50+ words
    overall_score = (keyword_score * 0.4) + (length_score * 0.6)
    
    return {
        "score": round(overall_score, 1),
        "spontaneous_fluency_score": 60,
        "depth_of_thought_score": 50,
        "advanced_vocabulary_score": keyword_score,
        "structural_coherence_score": 50,
        "keyword_matches": keyword_matches,
        "total_keywords": total_keywords,
        "fluency_score": 60,
        "grammar_score": 50,
        "is_correct": overall_score >= 70,
        "completed": overall_score >= 80,
        "suggested_improvement": "Try to speak more naturally and include more of the expected keywords in your response.",
        "strengths": ["Attempted the topic"],
        "areas_for_improvement": ["Need more spontaneous fluency", "Include more expected keywords"],
        "fluency_analysis": "Basic response provided",
        "thought_analysis": "Simple response structure",
        "vocabulary_analysis": f"Used {keyword_matches}/{total_keywords} expected keywords",
        "coherence_analysis": "Basic organization"
    }



def evaluate_response_ex2_stage6(expected_keywords, user_text, scenario_text, model_response, evaluation_criteria):
    """
    Evaluate Stage 6 Exercise 2 (Roleplay - Handle a Sensitive Scenario) responses using ChatGPT.
    
    Args:
        expected_keywords: List of expected keywords from the scenario
        user_text: Transcribed user response
        scenario_text: The sensitive scenario description
        model_response: Expected model response for comparison
        evaluation_criteria: Dictionary with evaluation weights
    
    Returns:
        Dictionary with evaluation results
    """
    try:
        print(f"🔄 [EVAL] Starting Stage 6 Exercise 2 evaluation")
        print(f"📝 [EVAL] Scenario: {scenario_text}")
        print(f"🎤 [EVAL] User response: {user_text}")
        print(f"🔑 [EVAL] Expected keywords: {expected_keywords}")
        
        # Extract evaluation criteria weights
        tone_control_weight = evaluation_criteria.get("tone_control", 30)
        empathy_authority_balance_weight = evaluation_criteria.get("empathy_authority_balance", 25)
        clarity_communication_weight = evaluation_criteria.get("clarity_communication", 25)
        conflict_resolution_weight = evaluation_criteria.get("conflict_resolution", 20)
        
        # Create sophisticated evaluation prompt
        evaluation_prompt = f"""
You are an expert English language evaluator for C2-level sensitive scenario roleplay exercises. Evaluate the following response based on the given criteria.

SCENARIO: {scenario_text}

USER RESPONSE: {user_text}

EXPECTED KEYWORDS: {', '.join(expected_keywords)}

MODEL RESPONSE (for reference): {model_response}

EVALUATION CRITERIA:
1. Tone Control (Weight: {tone_control_weight}%): Appropriate emotional tone, diplomatic language, professional demeanor
2. Empathy vs Authority Balance (Weight: {empathy_authority_balance_weight}%): Balancing understanding with assertiveness, showing care while maintaining position
3. Clarity & Communication (Weight: {clarity_communication_weight}%): Clear, precise language, effective message delivery, professional articulation
4. Conflict Resolution (Weight: {conflict_resolution_weight}%): Problem-solving approach, constructive dialogue, resolution-oriented communication

Please provide a comprehensive evaluation in the following JSON format:

{{
    "overall_score": <0-100>,
    "tone_control_score": <0-100>,
    "empathy_authority_balance_score": <0-100>,
    "clarity_communication_score": <0-100>,
    "conflict_resolution_score": <0-100>,
    "keyword_matches": <number of keywords used>,
    "total_keywords": <total number of expected keywords>,
    "tone_analysis": "<detailed analysis of tone control>",
    "empathy_authority_analysis": "<detailed analysis of empathy vs authority balance>",
    "clarity_analysis": "<detailed analysis of clarity and communication>",
    "conflict_resolution_analysis": "<detailed analysis of conflict resolution approach>",
    "strengths": ["<list of key strengths>"],
    "areas_for_improvement": ["<list of specific improvement areas>"],
    "suggested_improvement": "<comprehensive improvement suggestion>",
    "is_correct": <true/false based on overall quality>,
    "completed": <true if score >= 80, false otherwise>
}}

Focus on C2-level expectations: sophisticated diplomatic language, emotional intelligence, professional communication, and effective conflict resolution strategies.
"""

        print(f"🔄 [EVAL] Sending evaluation request to ChatGPT")
        
        # Get ChatGPT response
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert English language evaluator for C2-level sensitive scenario roleplay exercises. Provide detailed, professional evaluations in the exact JSON format requested."},
                {"role": "user", "content": evaluation_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        # Extract and parse the response
        evaluation_text = response.choices[0].message.content.strip()
        print(f"📊 [EVAL] ChatGPT response received: {evaluation_text[:200]}...")
        
        # Parse JSON response
        try:
            evaluation_data = json.loads(evaluation_text)
            print(f"✅ [EVAL] JSON parsed successfully")
        except json.JSONDecodeError as e:
            print(f"❌ [EVAL] JSON parsing error: {str(e)}")
            # Fallback evaluation
            return create_fallback_evaluation_sensitive_scenario(user_text, expected_keywords, scenario_text)
        
        # Validate and process the evaluation data
        overall_score = evaluation_data.get("overall_score", 0)
        tone_control_score = evaluation_data.get("tone_control_score", 0)
        empathy_authority_balance_score = evaluation_data.get("empathy_authority_balance_score", 0)
        clarity_communication_score = evaluation_data.get("clarity_communication_score", 0)
        conflict_resolution_score = evaluation_data.get("conflict_resolution_score", 0)
        keyword_matches = evaluation_data.get("keyword_matches", 0)
        total_keywords = evaluation_data.get("total_keywords", len(expected_keywords))
        
        # Calculate weighted score
        weighted_score = (
            (tone_control_score * tone_control_weight / 100) +
            (empathy_authority_balance_score * empathy_authority_balance_weight / 100) +
            (clarity_communication_score * clarity_communication_weight / 100) +
            (conflict_resolution_score * conflict_resolution_weight / 100)
        )
        
        # Determine completion status
        is_correct = weighted_score >= 70
        completed = weighted_score >= 80
        
        print(f"📊 [EVAL] Evaluation results:")
        print(f"   Overall Score: {weighted_score:.1f}")
        print(f"   Tone Control: {tone_control_score}")
        print(f"   Empathy vs Authority Balance: {empathy_authority_balance_score}")
        print(f"   Clarity & Communication: {clarity_communication_score}")
        print(f"   Conflict Resolution: {conflict_resolution_score}")
        print(f"   Keyword Matches: {keyword_matches}/{total_keywords}")
        print(f"   Completed: {completed}")
        
        return {
            "score": round(weighted_score, 1),
            "tone_control_score": tone_control_score,
            "empathy_authority_balance_score": empathy_authority_balance_score,
            "clarity_communication_score": clarity_communication_score,
            "conflict_resolution_score": conflict_resolution_score,
            "keyword_matches": keyword_matches,
            "total_keywords": total_keywords,
            "fluency_score": tone_control_score,  # For compatibility
            "grammar_score": clarity_communication_score,  # For compatibility
            "is_correct": is_correct,
            "completed": completed,
            "suggested_improvement": evaluation_data.get("suggested_improvement", ""),
            "strengths": evaluation_data.get("strengths", []),
            "areas_for_improvement": evaluation_data.get("areas_for_improvement", []),
            "tone_analysis": evaluation_data.get("tone_analysis", ""),
            "empathy_authority_analysis": evaluation_data.get("empathy_authority_analysis", ""),
            "clarity_analysis": evaluation_data.get("clarity_analysis", ""),
            "conflict_resolution_analysis": evaluation_data.get("conflict_resolution_analysis", "")
        }
        
    except Exception as e:
        print(f"❌ [EVAL] Error in Stage 6 Exercise 2 evaluation: {str(e)}")
        return create_fallback_evaluation_sensitive_scenario(user_text, expected_keywords, scenario_text)

def create_fallback_evaluation_sensitive_scenario(user_text, expected_keywords, scenario_text):
    """Create a fallback evaluation when ChatGPT fails for sensitive scenarios"""
    print(f"🔄 [EVAL] Creating fallback evaluation for sensitive scenario")
    
    # Simple keyword matching
    user_words = set(user_text.lower().split())
    keyword_matches = sum(1 for keyword in expected_keywords if keyword.lower() in user_words)
    total_keywords = len(expected_keywords)
    
    # Basic scoring
    keyword_score = (keyword_matches / total_keywords) * 100 if total_keywords > 0 else 0
    length_score = min(len(user_text.split()) / 40 * 100, 100)  # Target: 40+ words for sensitive scenarios
    overall_score = (keyword_score * 0.4) + (length_score * 0.6)
    
    return {
        "score": round(overall_score, 1),
        "tone_control_score": 60,
        "empathy_authority_balance_score": 50,
        "clarity_communication_score": 60,
        "conflict_resolution_score": 50,
        "keyword_matches": keyword_matches,
        "total_keywords": total_keywords,
        "fluency_score": 60,
        "grammar_score": 60,
        "is_correct": overall_score >= 70,
        "completed": overall_score >= 80,
        "suggested_improvement": "Try to use more diplomatic language and include more of the expected keywords in your response.",
        "strengths": ["Attempted the sensitive scenario"],
        "areas_for_improvement": ["Need more diplomatic tone", "Include more expected keywords"],
        "tone_analysis": "Basic response provided",
        "empathy_authority_analysis": "Simple approach to sensitive situation",
        "clarity_analysis": f"Used {keyword_matches}/{total_keywords} expected keywords",
        "conflict_resolution_analysis": "Basic conflict resolution attempt"
    }

def evaluate_response_ex3_stage6(user_response: str, topic: str, expected_keywords: list, vocabulary_focus: list, academic_expressions: list, model_response: str, expected_structure: str) -> dict:
    """
    Evaluate Stage 6 Exercise 3 (Critical Opinion Builder) responses using OpenAI GPT-4o.
    
    This function evaluates C2 Advanced level critical opinion building based on:
    - Argument structure and logical flow
    - Academic expression usage
    - Critical thinking depth
    - Vocabulary sophistication
    - Balanced viewpoint presentation
    
    Args:
        user_response (str): The user's written opinion response
        topic (str): The controversial topic they were asked to discuss
        expected_keywords (list): Expected keywords to include
        vocabulary_focus (list): Domain-specific vocabulary to evaluate
        academic_expressions (list): Expected academic expressions to use
        model_response (str): Example of a well-structured response for comparison
        expected_structure (str): Expected argument structure
    
    Returns:
        dict: Comprehensive evaluation results with scores and detailed feedback
    """
    print(f"🔍 [EVAL] Evaluating Stage 6 Exercise 3 response: {user_response[:100]}...")
    print(f"📝 [EVAL] Topic: {topic}")
    print(f"📝 [EVAL] Expected keywords: {expected_keywords}")
    print(f"📝 [EVAL] Vocabulary focus: {vocabulary_focus}")
    print(f"📝 [EVAL] Academic expressions: {academic_expressions}")
    print(f"📝 [EVAL] Expected structure: {expected_structure}")
    
    try:
        # Create comprehensive evaluation prompt
        evaluation_prompt = f"""
You are an expert English language evaluator for C2 Advanced level critical opinion building. You are a well experienced prompt engineer.

**TOPIC:** {topic}
**USER'S RESPONSE:** "{user_response}"
**MODEL ANSWER FOR REFERENCE:** "{model_response}"
**EXPECTED STRUCTURE:** {expected_structure}
**EXPECTED KEYWORDS:** {expected_keywords}
**VOCABULARY FOCUS:** {vocabulary_focus}
**ACADEMIC EXPRESSIONS TO USE:** {academic_expressions}

**EVALUATION CRITERIA:**
1. **Argument Structure (30 points):** How well does the response follow the expected structure (Thesis → Supporting Arguments → Counterpoint → Conclusion)?
2. **Logical Flow (25 points):** Is there clear logical progression and coherent reasoning throughout the argument?
3. **Academic Expressions (25 points):** How effectively are academic expressions and transitional phrases used?
4. **Critical Thinking (20 points):** Does the response demonstrate sophisticated critical thinking and balanced analysis?

**SCORING GUIDELINES:**
- 90-100: Exceptional critical analysis with sophisticated argumentation
- 80-89: Excellent argument structure with strong academic language
- 70-79: Good critical thinking with some areas for improvement
- 60-69: Satisfactory but needs refinement in structure or expression
- Below 60: Needs significant improvement in multiple areas

**KEYWORD EVALUATION:**
- Count exact matches and close synonyms
- Consider variations in word forms
- Focus on meaningful usage rather than just inclusion
- Evaluate natural integration into the argument

**ACADEMIC EXPRESSION EVALUATION:**
- Assess natural usage of transitional phrases
- Evaluate appropriateness of academic language
- Consider variety and sophistication of expressions used

**TASK:** Provide a comprehensive evaluation with specific feedback and suggestions for improvement.

**REQUIRED JSON OUTPUT FORMAT:**
{{
    "score": <number between 0-100>,
    "is_correct": <boolean - true if score >= 75>,
    "completed": <boolean - true if score >= 80>,
    "keyword_matches": <number of expected keywords found>,
    "total_keywords": <total number of expected keywords>,
    "academic_expressions_used": <number of academic expressions found>,
    "total_academic_expressions": <total number of expected academic expressions>,
    "detailed_feedback": {{
        "argument_structure": "<specific feedback on argument structure>",
        "logical_flow": "<feedback on logical progression and coherence>",
        "academic_expressions": "<feedback on academic language usage>",
        "critical_thinking": "<feedback on critical analysis depth>",
        "vocabulary_usage": "<feedback on vocabulary sophistication>"
    }},
    "suggested_improvement": "<specific suggestions for improvement>",
    "strengths": ["<list of strengths in the response>"],
    "areas_for_improvement": ["<list of areas that need work>"],
    "structure_analysis": {{
        "thesis_present": <boolean>,
        "supporting_arguments": <number>,
        "counterpoint_addressed": <boolean>,
        "conclusion_present": <boolean>
    }}
}}
"""

        print(f"🤖 [EVAL] Sending evaluation request to ChatGPT...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert English language evaluator for C2 Advanced level critical opinion building."},
                {"role": "user", "content": evaluation_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        evaluation_text = response.choices[0].message.content.strip()
        print(f"📄 [EVAL] Raw ChatGPT response: {evaluation_text[:200]}...")
        
        # Try to extract JSON from the response
        try:
            # Look for JSON in the response
            json_start = evaluation_text.find('{')
            json_end = evaluation_text.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_content = evaluation_text[json_start:json_end]
                evaluation_result = json.loads(json_content)
                print(f"✅ [EVAL] Successfully parsed JSON evaluation")
            else:
                raise ValueError("No JSON found in response")
                
        except json.JSONDecodeError as e:
            print(f"❌ [EVAL] JSON parsing error: {str(e)}")
            print(f"📄 [EVAL] Attempted to parse: {evaluation_text}")
            
            # Fallback evaluation
            evaluation_result = {
                "score": 50,
                "is_correct": False,
                "completed": False,
                "keyword_matches": 0,
                "total_keywords": len(expected_keywords),
                "academic_expressions_used": 0,
                "total_academic_expressions": len(academic_expressions),
                "detailed_feedback": {
                    "argument_structure": "Unable to evaluate due to processing error",
                    "logical_flow": "Unable to evaluate due to processing error",
                    "academic_expressions": "Unable to evaluate due to processing error",
                    "critical_thinking": "Unable to evaluate due to processing error",
                    "vocabulary_usage": "Unable to evaluate due to processing error"
                },
                "suggested_improvement": "Please try again. Make sure to follow the expected structure and use academic expressions naturally.",
                "strengths": ["Response provided"],
                "areas_for_improvement": ["Evaluation processing error"],
                "structure_analysis": {
                    "thesis_present": False,
                    "supporting_arguments": 0,
                    "counterpoint_addressed": False,
                    "conclusion_present": False
                }
            }
        
        # Validate and sanitize the evaluation result
        score = evaluation_result.get("score", 50)
        if not isinstance(score, (int, float)) or score < 0 or score > 100:
            score = 50
            evaluation_result["score"] = score
        
        is_correct = evaluation_result.get("is_correct", score >= 75)
        completed = evaluation_result.get("completed", score >= 80)
        
        # Ensure keyword matches is valid
        keyword_matches = evaluation_result.get("keyword_matches", 0)
        total_keywords = evaluation_result.get("total_keywords", len(expected_keywords))
        
        if not isinstance(keyword_matches, int) or keyword_matches < 0:
            keyword_matches = 0
        if not isinstance(total_keywords, int) or total_keywords <= 0:
            total_keywords = len(expected_keywords)
        
        # Ensure academic expressions count is valid
        academic_expressions_used = evaluation_result.get("academic_expressions_used", 0)
        total_academic_expressions = evaluation_result.get("total_academic_expressions", len(academic_expressions))
        
        if not isinstance(academic_expressions_used, int) or academic_expressions_used < 0:
            academic_expressions_used = 0
        if not isinstance(total_academic_expressions, int) or total_academic_expressions <= 0:
            total_academic_expressions = len(academic_expressions)
        
        evaluation_result.update({
            "is_correct": is_correct,
            "completed": completed,
            "keyword_matches": keyword_matches,
            "total_keywords": total_keywords,
            "academic_expressions_used": academic_expressions_used,
            "total_academic_expressions": total_academic_expressions
        })
        
        print(f"📊 [EVAL] Final evaluation result:")
        print(f"   - Score: {score}")
        print(f"   - Is correct: {is_correct}")
        print(f"   - Completed: {completed}")
        print(f"   - Keyword matches: {keyword_matches}/{total_keywords}")
        print(f"   - Academic expressions: {academic_expressions_used}/{total_academic_expressions}")
        
        return evaluation_result
        
    except Exception as e:
        print(f"❌ [EVAL] Error in evaluate_response_ex3_stage6: {str(e)}")
        
        # Return fallback evaluation
        return {
            "score": 50,
            "is_correct": False,
            "completed": False,
            "keyword_matches": 0,
            "total_keywords": len(expected_keywords),
            "academic_expressions_used": 0,
            "total_academic_expressions": len(academic_expressions),
            "detailed_feedback": {
                "argument_structure": "Evaluation error occurred",
                "logical_flow": "Evaluation error occurred",
                "academic_expressions": "Evaluation error occurred",
                "critical_thinking": "Evaluation error occurred",
                "vocabulary_usage": "Evaluation error occurred"
            },
            "suggested_improvement": "Please try again. Focus on following the expected structure and using academic expressions naturally.",
            "strengths": ["Attempted response"],
            "areas_for_improvement": ["Technical evaluation error"],
            "structure_analysis": {
                "thesis_present": False,
                "supporting_arguments": 0,
                "counterpoint_addressed": False,
                "conclusion_present": False
            }
        }

