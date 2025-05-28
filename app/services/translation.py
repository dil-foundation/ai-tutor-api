from openai import OpenAI
from app.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def translate_urdu_to_english(text: str) -> str:
    
    prompt = f"Translate the following Urdu sentence into fluent and grammatically correct English: '{text} '"
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content.strip()
