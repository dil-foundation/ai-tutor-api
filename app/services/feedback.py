from openai import OpenAI
from app.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def get_fluency_feedback(user_text: str, expected_text: str) -> dict:
    prompt = f"""
You are an English pronunciation and tone evaluator.

The user was expected to say: "{expected_text}"
The user actually said (transcribed): "{user_text}"

Please evaluate and return the result in the following format:

Pronunciation score: <percentage>% (based on clarity and accuracy)
Tone & Intonation: <one-word rating like Excellent, Good, Fair, Poor>
Feedback: <short one-line constructive tip>

Only provide the output in that format. No extra text.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        output = response.choices[0].message.content.strip()

        lines = output.split("\n")
        result = {
            "pronunciation_score": lines[0].split(":")[1].strip(),
            "tone_intonation": lines[1].split(":")[1].strip(),
            "feedback": lines[2].split(":", 1)[1].strip()
        }

        return result

    except Exception as e:
        print("❌ Error during fluency evaluation:", str(e))
        # Default fallback response
        return {
            "pronunciation_score": "0%",
            "tone_intonation": "Poor",
            "feedback": "Thank you"
        }


def evaluate_response(expected: str, actual: str) -> dict:
    """
    Wrapper function that calls GPT-based feedback engine and returns:
    {
        "correct": bool,
        "pronunciation_score": "85%",
        "tone_intonation": "Good",
        "feedback": "Try to speak more clearly at the end."
    }
    """
    feedback = get_fluency_feedback(actual, expected)

    # Mark as correct if score ≥ 80%
    try:
        score_str = feedback["pronunciation_score"].replace("%", "")
        score = int(score_str)
        is_correct = score >= 65
    except:
        is_correct = False

    feedback["correct"] = is_correct
    return feedback
