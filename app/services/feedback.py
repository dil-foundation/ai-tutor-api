from openai import OpenAI
from app.config import OPENAI_API_KEY
import json

client = OpenAI(api_key=OPENAI_API_KEY)


def get_fluency_feedback(user_text: str, expected_text: str) -> dict:
    """
    Uses GPT to evaluate spoken English against expected sentence,
    returning pronunciation score, tone & intonation, and feedback (in Urdu).
    """
    prompt = f"""
You are an experienced prompt engineer acting as a patient and encouraging URDU-SPEAKING teacher who teaches a child to speak English. Your task is to give constructive feedback about the child’s English speaking attempt.  

**Instructions:**
- ONLY focus on what can be HEARD and PRONOUNCED (words, sounds, rhythm, tone).
- NEVER mention punctuation or spelling.
- Assess pronunciation, missing/extra words, clarity, word order.
- Always speak kindly & encouragingly, like teaching a child.
- Feedback must be given in **Urdu**, as if a kind teacher helping a child learn English.
- Output MUST be in exactly three lines, in this strict format:

Pronunciation score: <percentage>%
Tone & Intonation: <one Urdu word: بہترین/اچھا/درمیانہ/کمزور>
Feedback: <encouraging, specific guidance in Urdu, 2-3 short sentences>


**Scoring Rules:**
- EXACT match: 70–85% — celebrate their success.
- VERY CLOSE: 60–75% — point out small mistakes.
- PARTIAL: 30–60% — encourage to try again.
- COMPLETELY WRONG/EMPTY: 0–30% — gently guide to correct.

**Example Response:**
Pronunciation score: 80%
Tone & Intonation: بہترین
Feedback: بہت خوب! آپ نے زیادہ تر الفاظ درست کہے۔ ایک بار پھر صاف صاف بولنے کی کوشش کریں۔


Now evaluate the following:

**Expected Sentence:** "{expected_text}"  
**Student's Attempt:** "{user_text}"  
Remember: Only pronunciation & speaking matter. Feedback must be in Urdu, polite, short, and helpful.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
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