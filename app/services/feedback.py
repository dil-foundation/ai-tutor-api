from openai import OpenAI
from app.config import OPENAI_API_KEY

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
