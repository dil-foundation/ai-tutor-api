from openai import OpenAI
from app.config import OPENAI_API_KEY
import json
import re

client = OpenAI(api_key=OPENAI_API_KEY)

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

Very Important: Do NOT comment on spelling, capitalization, or punctuation differences at all — ignore these completely. Treat “Where are you” and “where are you?” as identical if spoken that way.
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
Feedback: <2-3 short English sentences giving warm, encouraging guidance. Use simple, kind words like “Great job”, “Try again”, “Well done”, etc.>

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

Your task is to give **constructive, warm feedback** in **Urdu script**, based only on the student’s **spoken attempt** (not spelling or punctuation).  
Your tone should reflect a **formal yet friendly, soft-spoken female teacher**, guiding the learner gently and supportively.

Very Important: Do NOT comment on spelling, capitalization, or punctuation differences at all — ignore these completely. Treat “Where are you” and “where are you?” as identical if spoken that way.
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

Now evaluate the student’s speaking attempt:

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

def analyze_english_input_eng_only(user_text: str) -> dict:
    """
    Analyzes English input and returns conversation text for TTS audio playback.
    Simplified to only return what the frontend actually needs.
    """
    prompt = f"""
You are an experienced and professional English tutor AI designed to help non-native speakers, especially beginners and children, improve their spoken English. 
Your role is to analyze the user's spoken sentence, identify any grammar mistakes or heavy accent-related issues, and respond in a kind, professional, and pedagogical way.

Your response should:
- Begin by repeating what the user said, so they feel heard.
- Clearly explain what mistake (if any) the user made, in simple and understandable language.
- Teach the correct form of the sentence, and explicitly say it at the end.
- Use simple grammar and vocabulary so that even a child can understand.
- Be warm, encouraging, and conversational — but structured and clear.
- At the end, say this exact phrase:
  **The correct form of your sentence would be: "<corrected_text>". If you need more help with grammar or anything else, feel free to ask.**

Here is the user's spoken text: "{user_text}"

Please respond ONLY with a **valid JSON**, and nothing else. Do not include any explanations, notes, or markdown code blocks.

JSON format:
{{
    "conversation_text": "a friendly and clear teaching statement. Start by saying what the user said, then explain the mistake, and finally say: 'The correct form of your sentence would be: \"<corrected_text>\". If you need more help with grammar or anything else, feel free to ask.'"
}}

If no issues are found, in conversation_text praise the user warmly, repeat their sentence, and encourage them to say something else.

Be encouraging, constructive, and speak in a way that a beginner or a child can easily understand.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )

        output = response.choices[0].message.content.strip()
        print(f"🔍 [ENGLISH_ONLY] GPT Raw Output: {output}")

        # clean if wrapped in ```json ... ```
        match = re.search(r"```json\s*(.*?)\s*```", output, re.DOTALL)
        if match:
            output_clean = match.group(1)
        else:
            output_clean = output

        try:
            result = json.loads(output_clean)
            validate_fields_simplified(result)
            print(f"✅ [ENGLISH_ONLY] Parsed JSON: {result}")
            return result
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"🔄 Trying regex fallback…")
            return extract_feedback_from_text_simplified(output_clean, user_text)

    except Exception as e:
        print(f"❌ [ENGLISH_ONLY] Error during analysis: {str(e)}")
        return fallback_response_simplified(user_text)


def validate_fields_simplified(result: dict):
    required_fields = ["conversation_text"]
    for field in required_fields:
        if field not in result:
            raise ValueError(f"Missing required field: {field}")


def extract_feedback_from_text_simplified(output: str, user_text: str) -> dict:
    """
    Fallback method: extract conversation_text from text using regular expressions.
    """
    def extract(pattern, text, default):
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else default

    conversation_text = extract(r'"conversation_text"\s*:\s*"(.*?)"', output,
        f"Wonderful! You said: '{user_text}', and that was perfect! Can you try saying another sentence?")
    
    result = {
        "conversation_text": conversation_text
    }
    print(f"✅ [ENGLISH_ONLY] Extracted with Regex: {result}")
    return result


def fallback_response_simplified(user_text: str) -> dict:
    """
    Returns a default response if everything fails.
    """
    return {
        "conversation_text": f"Wonderful! You said: '{user_text}', and that was perfect! Can you try saying another sentence?"
    }
