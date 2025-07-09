from openai import OpenAI
from app.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def translate_urdu_to_english(text: str) -> str:
    prompt = (
        f"Translate the following Urdu sentence to English. "
        f"Only output the translated English sentence, nothing else. "
        f"Do not include any explanation, comments, or transliterations. "
        f"Here is the sentence:\n{text}\n"
        f"Output:"
    )

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    result = response.choices[0].message.content.strip()
    print("response of the english sentence:", result)
    return result
