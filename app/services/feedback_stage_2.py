from openai import OpenAI

client = OpenAI()

def generate_feedback(transcript: str, example: str, keywords: list[str]) -> dict:
    """
    Uses OpenAI GPT to evaluate a user's spoken English narration for relevance, keyword use, and fluency.

    Returns:
        dict with:
            - score (float): semantic + lexical match score (%)
            - feedback (str): concise one-line improvement tip
    """
    keyword_str = ", ".join(keywords)

    prompt = f"""
You are an expert AI language evaluator for an English learning platform.

Your task is to analyze the user's response to a speaking prompt about daily routines. Assess it for:
1. Semantic relevance to the sample answer
2. Fluency and clarity of expression
3. Presence of important daily routine keywords

---

Expected Sample Answer:
"{example}"

User's Transcribed Response:
"{transcript}"

Important keywords the user should ideally mention: {keyword_str}

---

Instructions:
- Compare the user's answer with the sample for semantic similarity.
- Check if any of the expected keywords are used (case-insensitive).
- Assign a score out of 100% based on clarity, relevance, and keyword presence.
- Provide 1 short, professional feedback line with either a constructive tip or praise.

Respond strictly in this format:
Score: <number>%
Feedback: <1-line feedback>

Example:
Score: 82%
Feedback: You covered the key actions well—focus slightly more on sentence structure next time.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )

    output = response.choices[0].message.content.strip()
    print("🔍 Raw GPT Feedback:\n", output)

    # Parse structured response
    lines = output.split("\n")
    score_line = lines[0].split(":")[1].strip().replace('%', '')
    feedback_line = lines[1].split(":", 1)[1].strip()

    return {
        "score": float(score_line),
        "feedback": feedback_line
    }
