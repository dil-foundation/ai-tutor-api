import openai
from openai import OpenAI

client = OpenAI()

def get_fluency_feedback(user_text: str, expected_text: str) -> str:
    prompt = f"""
You are an English language speaking and pronunciation evaluator.

The user was expected to say: "{expected_text}"
The user actually said (transcribed): "{user_text}"

Please:
- Evaluate how fluent the user was
- Identify pronunciation or grammar mistakes if any
- Give a brief, constructive feedback in 3-4 sentences
- End with a motivational comment to help the user improve
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()
