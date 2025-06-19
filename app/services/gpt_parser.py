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
You are an AI quiz generator trained to extract quiz questions from educational text. Your output must follow LearnDash-compatible question types and return in the following structured JSON format:

{{
    "title": "Title of the quiz (derived from the first heading or sentence)",
    "questions": [
        {{
            "question": "Question text here",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Correct answer text or comma-separated answers",
            "type": "single"  // One of the allowed types listed below
        }}
    ]
}}

Each question must include:
- A clearly stated question
- A list of answer options (if applicable)
- The correct answer(s)
- The question type (required)

Allowed question types (based on LearnDash format):
- "single" (single correct choice)
- "multiple" (multiple correct choices)
- "true_or_false"
- "fill_in_the_blank"
- "short_answer"
- "essay"
- "matching"
- "sorting"
- "matrix_sort"

Respond only with a valid JSON object. Do not include explanations, markdown, or natural language outside of the JSON structure.

Here is the educational text to process:
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
