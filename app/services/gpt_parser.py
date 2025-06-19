import os
import json
import re
from app.schemas.pdf_quiz import QuizItem
from typing import List, Dict
from openai import OpenAI

client = OpenAI()

def extract_json_from_response(content: str) -> Dict:
    """
    Extract the first valid JSON object from the GPT response using regex and parse it.
    """
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        json_str = match.group()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print("❌ JSON parsing error:", e)
            return {"error": "Invalid JSON format from GPT"}
    else:
        print("❌ No JSON found in GPT response")
        return {"error": "No JSON found in response"}

def extract_quiz_from_text_using_gpt(text: str) -> Dict:
    prompt = f"""
You are an AI that extracts multiple choice questions from text. 
Extract all MCQs from the following text and return them as JSON in this format:

{{
    "title": "Title of the quiz (first heading or line)",
    "questions": [
        {{
            "question": "Question text",
            "options": ["A", "B", "C", "D"],
            "answer": "Answer Text"
        }}
    ]
}}

Here is the text:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts quiz questions."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
   
    # 🔍 Debug and parse
    content = response.choices[0].message.content.strip()
    print("🧠 GPT Response:\n", content)

    return extract_json_from_response(content)
