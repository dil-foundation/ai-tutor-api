from openai import OpenAI

client = OpenAI()  # This uses the OPENAI_API_KEY from your environment automatically

def get_fluency_feedback(user_text: str, expected_text: str) -> dict:
    prompt = f"""
You are an English pronunciation and tone evaluator.

The user was expected to say: "{expected_text}"
The user actually said (transcribed): "{user_text}"

Please evaluate and return the result in the following format:

Pronunciation score: <percentage>% (based on clarity and accuracy)
Feedback: <short one-line constructive tip>

Only provide the output in that format. No extra text.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    output = response.choices[0].message.content.strip()

    lines = output.split("\n")
    result = {
        "pronunciation_score": lines[0].split(":")[1].strip(),
        "feedback": lines[1].split(":", 1)[1].strip()
    }

    return result
