import json
from openai import OpenAI

client = OpenAI()

def evaluate_dialogue_with_gpt(ai_prompt: str, expected_keywords: str, user_response: str) -> dict:
    prompt = f"""
You are a helpful AI English tutor assisting language learners.

Your task is to evaluate a student's spoken response in an English conversation practice.

Details:
- AI's question: "{ai_prompt}"
- Key expected keywords (not strict answers, just contextual hints): "{expected_keywords}"
- Student's transcribed response: "{user_response}"

Evaluate the student's response based on the following:

1. **Grammar** - Check for proper sentence structure and correctness.
2. **Fluency** - How natural and smooth the sentence would sound when spoken.
3. **Relevance** - Does the response logically answer the AI's question? (Note: the student may give a different valid answer; do not penalize this.)
4. **Keyword Presence** - Are at least some of the expected keywords or relevant words included?

Return a JSON response in this structure:

{{
  "feedback": "Detailed and constructive feedback with 2-3 improvement tips.",
  "grammar_score": [0-10],
  "fluency_score": [0-10],
  "relevance_score": [0-10],
  "keyword_score": [0-10],
  "overall": [0-100]
}}

🎯 Key Instructions:
- The `expected_keywords` are just a hint. The answer must be evaluated on merit, not exact matches.
- Encourage and support the learner with positive tone and helpful suggestions.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    content = response.choices[0].message.content
    return json.loads(content)
