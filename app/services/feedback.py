from openai import OpenAI
from app.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def get_fluency_feedback(user_text: str, expected_text: str) -> dict:
    prompt = f"""
You are a patient and encouraging English teacher teaching a child student. Your role is to help them learn English pronunciation and speaking skills with kindness and clear guidance.

**Expected Sentence:** "{expected_text}"
**Student's Attempt:** "{user_text}"

**CRITICAL RULES FOR SPEAKING FEEDBACK:**
- ONLY focus on what can be HEARD and PRONOUNCED (words, sounds, rhythm, tone)
- NEVER mention punctuation (commas, question marks, periods) - these cannot be pronounced
- NEVER mention spelling differences that sound the same
- Focus on pronunciation, word order, missing words, extra words, and speaking clarity
- Be like a teacher helping a child learn to speak, not write

**IMPORTANT SCORING RULES:**
- If the student's text EXACTLY matches the expected text (word for word), give them 70-85% score and celebrate their success
- If the student's text is very close but has minor pronunciation differences, give them 60-75% score
- If the student's text has significant pronunciation differences, give them 30-60% score based on how close they are
- If the student's text is completely wrong or empty, give them 0-30% score

**Your Teaching Approach:**
1. **Be encouraging and patient** - like teaching a child to speak
2. **Identify pronunciation mistakes** - what words or sounds were wrong
3. **Provide clear speaking correction** - show them exactly what to say out loud
4. **Give pronunciation tips** - help them say it correctly
5. **Use simple, encouraging language** - make them feel confident
6. **Celebrate success** - when they get it right, praise them enthusiastically

**Evaluation Guidelines:**
- **Pronunciation Score:** 0-100% (based on spoken words and sounds only)
- **Tone & Intonation:** Excellent/Good/Fair/Poor
- **Feedback:** Specific, encouraging guidance for speaking

**Examples of Good Feedback:**

**For EXACT MATCHES (70-85% score):**
- "Excellent! Perfect pronunciation! You said '{expected_text}' exactly right. Your English speaking is getting better and better! Keep up the great work!"

**For VERY CLOSE MATCHES (60-75% score):**
- "Great job! You're very close. You said '{user_text}' but we need to say '{expected_text}'. You're almost there! Try saying '{expected_text}' one more time."

**For PARTIAL MATCHES (30-60% score):**
- "Good try! You said '{user_text}' but we need to say '{expected_text}'. Let's practice: '{expected_text}'. Remember to say each word clearly."

**For COMPLETELY WRONG (0-30% score):**
- "Let's try again! The correct sentence is '{expected_text}'. Say it with me: '{expected_text}'. You can do it!"

**Response Format:**
Pronunciation score: <percentage>% 
Tone & Intonation: <one-word rating>
Feedback: <encouraging, specific guidance like a teacher>

**Note**:The feedback sentence should be 2 to 3 sentence only.
**Remember:** Be encouraging, specific, and helpful. Guide them like a patient teacher would guide a child learning to speak English. Focus ONLY on pronunciation and speaking - never mention punctuation or spelling that doesn't affect pronunciation. When they get it right, celebrate their success!
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        output = response.choices[0].message.content.strip()

        lines = output.split("\n")
        result = {
            "pronunciation_score": lines[0].split(":")[1].strip(),
            "tone_intonation": lines[1].split(":")[1].strip(),
            "feedback": lines[2].split(":", 1)[1].strip()
        }

        print("result: ",result)

        return result

    except Exception as e:
        print("❌ Error during fluency evaluation:", str(e))
        # Default fallback response
        return {
            "pronunciation_score": "0%",
            "tone_intonation": "Poor",
            "feedback": "Let's try again! Say the complete sentence clearly."
        }


def evaluate_response(expected: str, actual: str) -> dict:
    """
    Wrapper function that calls GPT-based feedback engine and returns:
    {
        "correct": bool,
        "pronunciation_score": "85%",
        "tone_intonation": "Good",
        "feedback": "Try to speak more clearly at the end."
    }
    """
    feedback = get_fluency_feedback(actual, expected)

    try:
        print("feedback: ",feedback["pronunciation_score"])
        score_str = feedback["pronunciation_score"].replace("%", "")
        score = int(score_str)
        is_correct = score >= 70
    except:
        score = 0
        is_correct = False
    
    # Add "Please try again" if score is less than 70%
    feedback_text = feedback["feedback"]
    if score < 70:
        feedback_text += " Please try again."

    print("is_correct: ",is_correct)

    return {
        "feedback_text": feedback_text,
        "is_correct": is_correct,
        "pronunciation_score": feedback["pronunciation_score"],
        "tone_intonation": feedback["tone_intonation"]
    } 