from openai import OpenAI
from app.config import OPENAI_API_KEY
import json
import re

client = OpenAI(api_key=OPENAI_API_KEY)

def get_fluency_feedback(user_text: str, expected_text: str) -> dict:
    """
    Uses GPT to evaluate spoken English against expected sentence,
    returning pronunciation score, tone & intonation, and feedback (in Urdu).
    """
    prompt = f"""
You are an experienced prompt engineer acting as a **kind and encouraging Pakistani female Urdu-speaking teacher** helping a student learn to speak English fluently.
Your feedback must always reflect the tone, language, and grammar of a Pakistani woman speaking to a child.  
For example, always use feminine forms like "میں مدد کروں گی", "میں بتاؤں گی", etc., and never use masculine forms like "میں مدد کروں گا".

Your task is to give **constructive, warm feedback** in **Urdu script**, based only on the student’s **spoken attempt** (not spelling or punctuation).  
Your tone should reflect a **friendly, soft-spoken female teacher**, guiding the learner gently and supportively.

ONLY focus on what was heard — pronunciation, clarity, missing or extra words, tone, and intonation.  
Do NOT comment on spelling, punctuation, or written grammar.

🩷 Very Important:  
- All Urdu feedback must use **feminine voice** — correct gendered verb endings.  
  For example: **"کروں گی"** instead of **"کروں گا"**, **"گئی"** instead of **"گیا"**, etc.  
- Use **colloquial, everyday Urdu (بول چال کی زبان)** — like a friendly teacher would speak. Avoid overly formal or literary words.  
- Feedback should be kind, clear, and encouraging — as if helping a child.

Respond in **exactly 3 lines**, in this strict format:

Pronunciation score:<percentage>%
Tone & Intonation:بہترین / اچھا / درمیانہ / کمزور  
Feedback: <2-3 short Urdu sentences giving warm, encouraging guidance. Use simple, everyday words like دوبارہ، بہتر، زبردست, etc.>

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
✅ Always use feminine grammar and soft tone.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        output = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
        print("GPT raw output:\n", output)

        # Robust parsing s
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
            "feedback": "آئیے دوبارہ کوشش کرتے ہیں۔ جملہ صاف صاف بولیں۔"
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
    if score < 80:
        feedback_text += " دوبارہ کوشش کریں۔"
    else:
        feedback_text += " شاباش، اگلا جملہ آزمائیں۔"

    print("✅ is_correct: ", is_correct)

    return {
        "feedback_text": feedback_text,
        "is_correct": is_correct,
        "pronunciation_score": feedback["pronunciation_score"],
        "tone_intonation": feedback["tone_intonation"]
    }

def evaluate_response_ex1_stage1(expected_phrase: str, user_response: str) -> dict:
    """
    Evaluate the student's response to the expected phrase, returning:
    - 1-line feedback
    - overall score
    - is_correct: True if score >= 80 else False
    """
    prompt = f"""
You are an expert English language evaluator for a language-learning app.  
Your task is to assess a student's spoken response compared to an expected phrase.

Inputs:
- Expected phrase: "{expected_phrase}"
- Student's response: "{user_response}"

🎯 Criteria:
- Accuracy: Does the student's response match or convey the same meaning as the expected phrase?
- Grammar & Fluency: Is it grammatically correct and natural?
- Relevance: Does it appropriately respond to the expected phrase's intent?

🎯 Output:
- A JSON object in the following format:
{{
  "feedback": "1-line constructive feedback.",
  "overall_score": [integer 0-100],
  "is_correct": [true if score >=80, else false]
}}

Guidelines:
✅ If the student's response is perfectly correct or very good (close in meaning & form to expected), give a score ≥ 80 and set `is_correct: true`.
✅ If response is poor, irrelevant, or incorrect, give < 80 and set `is_correct: false`.
✅ Feedback should clearly explain why the response was good or how to improve — but only 1 line.

Respond ONLY with the JSON object, no extra text.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    # Extract the content string from the response object
    json_content = response.choices[0].message.content.strip()

    # Parse JSON content into Python dict
    return json.loads(json_content)