# Stage 2 - Exercise 2 (Questions & Answers Practice - Responding to WH-questions)

from openai import OpenAI
from typing import List, Dict

client = OpenAI()

def evaluate_wh_response(transcript: str, expected_answers: List[str], keywords: List[str], tense: str) -> Dict:
    """
    Evaluate the user's spoken response to a WH-question using GPT only (no grammar lib).

    Returns:
        dict with:
            - score (float): 0-100
            - grammar_errors (List[str]): extracted by GPT
            - feedback (str): one-line improvement tip
    """
    # Format the example answers and keywords for the prompt
    example_answers = "\n".join([f"- {ans}" for ans in expected_answers])
    keyword_str = ", ".join(keywords)

    # GPT prompt with flexible matching logic
    prompt = f"""
You are an advanced AI English tutor and evaluator for a speaking practice app.

The learner has responded to a WH-question (e.g., "Where do you live?"). Your task is to evaluate their answer based on:

1. Whether it meaningfully and correctly answers the question (semantic relevance).
2. Fluency and grammar correctness.
3. Proper use of verb tense (Target tense: {tense}).
4. Inclusion of helpful or related vocabulary (if applicable).

Note:
- The sample answers and keywords below are only examples.
- The user may give other valid answers (e.g., different cities, foods, times) that should still be scored well.
- Don't penalize if the user doesn't use the exact keywords, as long as the meaning is clear and fluent.

---

Sample acceptable answers:
{example_answers}

User's transcribed response:
"{transcript}"

Suggested keywords to guide context (optional): {keyword_str}

---

Respond strictly in this format:
Score: <score>%  
Grammar Errors: <comma-separated list of grammar issues or "None">  
Feedback: <1-line helpful and professional feedback>
"""

    try:
        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )

        output = response.choices[0].message.content.strip()
        print("🔍 GPT Raw Output:\n", output)

        # Parse GPT output
        lines = output.split("\n")

        score = float(lines[0].split(":")[1].strip().replace("%", ""))
        grammar_errors_line = lines[1].split(":", 1)[1].strip()
        grammar_errors = [e.strip() for e in grammar_errors_line.split(",")] if grammar_errors_line.lower() != "none" else []
        feedback = lines[2].split(":", 1)[1].strip()

        return {
            "score": round(score, 2),
            "grammar_errors": grammar_errors,
            "feedback": feedback
        }

    except Exception as e:
        print("❌ GPT Evaluation Error:", str(e))
        return {
            "score": 0.0,
            "grammar_errors": [],
            "feedback": "Evaluation failed. Please try again."
        }
