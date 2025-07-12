from openai import OpenAI
from app.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def translate_urdu_to_english(text: str) -> str:
    prompt = (
        "You are a professional English teacher and translator.\n"
        "Your task is to take any sentence given to you — whether it is in Urdu, Hindi, or any other language — "
        "and convert it into a natural, fluent, grammatically correct English sentence.\n\n"
        "✅ Only output the translated and corrected English sentence.\n"
        "✅ Do not include any explanation, comments, or transliterations.\n"
        "✅ Make sure the sentence is polished for proper grammar and pronunciation.\n\n"
        "Here is the sentence:\n"
        f"{text}\n\n"
        "Output:"
    )

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    result = response.choices[0].message.content.strip()
    print("response of the english sentence:", result)
    return result


def translate_to_urdu(text: str) -> str:
    prompt = (
        "You are an expert Pakistani Urdu translator and linguistic consultant.\n"
        "Your task is to take the provided sentence — which can be in English, Roman Urdu, Hindi, or any other language — "
        "and output the most accurate, natural, and properly written **Pakistani Urdu script** equivalent.\n\n"
        "🎯 Guidelines:\n"
        "✅ Only output the translated Pakistani Urdu sentence.\n"
        "✅ Do not include any comments, explanations, Roman transliteration, or additional text.\n"
        "✅ Ensure proper grammar, spelling, and diacritics where appropriate.\n"
        "✅ The translation must sound natural to a native Pakistani Urdu speaker.\n\n"
        f"Here is the sentence:\n{text}\n\n"
        "Output:"
    )

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    result = response.choices[0].message.content.strip()
    print("response of the urdu sentence:", result)
    return result