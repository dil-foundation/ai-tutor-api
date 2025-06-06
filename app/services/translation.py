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

def detect_language(text: str) -> str:
    prompt = f"""
You are a language detector. Given a sentence, detect its most likely language.

- If multiple languages are mixed (e.g., Urdu + English, Urdu + Hindi), return "Urdu".
- If it's phonetically written (e.g., Tamil in English script), return the actual language (e.g., "Tamil").
- Do not explain your answer.
- Return only the language name like: "Urdu", "Hindi", "Tamil", "English", etc.
- If there was the empty text return "nothing".

Sentence:
{text}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        language = response.choices[0].message.content.strip()
        return language
    except Exception as e:
        print(f"❌ Error detecting language: {str(e)}")
        return "Unknown"

