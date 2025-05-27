# def evaluate_cefr_level(user_text: str) -> str:
#     system_prompt = (
#         "You are a professional English tutor and CEFR evaluator. "
#         "Evaluate the user's English writing and assign one CEFR stage (A1, A2, B1, B2, C1, or C2). "
#         "Only respond with the level (e.g., A2)."
#     )

#     prompt = f"User's writing:\n\"{user_text}\""

#     response = openai.ChatCompletion.create(
#         model="gpt-4-turbo",
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": prompt}
#         ],
#         max_tokens=10,
#         temperature=0.3,
#     )

from openai import OpenAI
from fastapi import HTTPException

client = OpenAI()

def evaluate_cefr_level(writing_sample: str) -> str:
    try:
        prompt = f"""
You are a professional English tutor and CEFR evaluator.

Evaluate the following English writing sample and classify it into CEFR stages: A0, A1, A2, B1, B2, C1, or C2.

If the writing shows no understanding of English, consists of broken grammar, misspelled words, or is mostly nonsensical, assign the level as 'A0'.

Writing Sample:
"{writing_sample}"

Respond with only one stage label: A0, A1, A2, B1, B2, C1, or C2.
"""
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print("❌ OpenAI Error:", str(e))
        raise HTTPException(status_code=500, detail="AI Evaluation Failed")
