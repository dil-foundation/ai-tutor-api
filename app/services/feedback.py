import openai
from openai import OpenAI

client = OpenAI()

def get_fluency_feedback(user_text: str) -> str:
    prompt = f"""
    Act as a language tutor. Give clear and constructive feedback on the user's English sentence below. Comment on pronunciation, fluency, grammar, and word usage.

    Sentence: "{user_text}"
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()
