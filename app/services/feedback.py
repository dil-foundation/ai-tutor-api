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
    raw_content = response.choices[0].message.content.strip()
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