# app/services/evaluator.py

import openai
from openai import OpenAI
import json

client = OpenAI()

def evaluate_response(question: str, expected_answer: str, user_response: str) -> dict:
    prompt = f"""
You are an AI English tutor evaluating a student's spoken response in a language learning application.

Below are the inputs:
- Question asked to the student: "{question}"
- Sample expected answer (for reference only): "{expected_answer}"
- Student's actual spoken response (transcribed): "{user_response}"

Your task is to evaluate the student's response based on the following criteria:

1. **Grammar** – Assess whether the sentence structure, verb tenses, and syntax are grammatically correct.
2. **Fluency** – Evaluate how naturally and smoothly the sentence would sound if spoken.
3. **Relevance** – Determine if the response logically and contextually answers the original question. *Note: The answer does not need to match the expected answer exactly — it only needs to be a valid, relevant response to the question.*
4. **Overall Score** – Provide a holistic score from 0 to 100 based on the above metrics.

⚠️ Important:
- The `expected_answer` is only a reference to indicate what kind of response is appropriate. Do not penalize the student for giving a different but contextually relevant answer.
- Do not overfit to the exact wording of the expected answer.
- Prioritize correct grammar, fluent expression, and contextual relevance to the question.

Return your output strictly as a JSON object in the following format:

{{
  "feedback": "Constructive feedback explaining the quality of the response and how to improve.",
  "grammar_score": [integer between 0 and 10],
  "fluency_score": [integer between 0 and 10],
  "relevance_score": [integer between 0 and 10],
  "overall": [integer between 0 and 100]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    # Extract the content string from the response object
    json_content = response.choices[0].message.content

    # Parse the JSON content string into a dictionary
    return json.loads(json_content)
