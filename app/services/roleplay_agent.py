from openai import OpenAI
import json
from app.redis_client import redis
from uuid import uuid4
from app.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

SCENARIO_FILE = "app/data/roleplay_scenarios.json"

def get_scenario_by_id(scenario_id: int):
    with open(SCENARIO_FILE, 'r', encoding='utf-8') as f:
        scenarios = json.load(f)
    return next((s for s in scenarios if s["id"] == scenario_id), None)

def create_session(scenario):
    session_id = str(uuid4())
    session_data = {
        "session_id": session_id,
        "history": [{"role": "system", "content": scenario["initial_prompt"]}],
        "chat_status": "progress"
    }
    redis.set(session_id, json.dumps(session_data), ex=3600)
    return session_id, scenario["initial_prompt"]

def check_chat_ended_via_gpt(history: list) -> bool:
    """
    Ask OpenAI to determine if the conversation is naturally ended.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a conversation monitor. Answer only 'yes' or 'no'."},
                {"role": "user", "content": f"Given this conversation history: {history}, has the conversation naturally ended? Answer 'yes' or 'no'."}
            ],
            temperature=0
        )
        decision = response.choices[0].message.content.strip().lower()
        return "yes" in decision
    except Exception as e:
        print(f"[❌ GPT Check Error]: {e}")
        return False


def update_session(session_id: str, user_input: str):
    session_data_json = redis.get(session_id)
    if not session_data_json:
        return None, None, "Session not found"

    session_data = json.loads(session_data_json)
    history = session_data.get("history", [])
    chat_status = session_data.get("chat_status", "progress")

    if chat_status == "end":
        return None, "end", "Chat has already ended."

    # Append user input
    history.append({"role": "user", "content": user_input})

    # Call OpenAI to get assistant response
    response = client.chat.completions.create(
        model="gpt-4",
        messages=history,
        temperature=0.7
    )

    ai_response = response.choices[0].message.content
    history.append({"role": "assistant", "content": ai_response})

    # ✅ Use GPT to check if the chat has ended
    is_ended = check_chat_ended_via_gpt(history)

    # Update session data
    session_data["history"] = history
    session_data["chat_status"] = "end" if is_ended else "progress"

    redis.set(session_id, json.dumps(session_data), ex=3600)

    return ai_response, session_data["chat_status"], None

def evaluate_conversation(history: list):
    try:
        evaluation_prompt = f"""
You are an English tutor evaluating a conversation between a student and an AI assistant. 
Give a score out of 100 based on fluency, grammar, vocabulary, and politeness. 
Provide feedback, suggestions (as a list), and remarks to help the student improve.

Conversation history:
{json.dumps(history, indent=2)}

Return JSON like:
{{
  "score": "85%",
  "feedback": "Try using full sentences and saying thank you.",
  "suggestions": ["Fluency", "Politeness"],
  "remarks": "Good effort. Use more varied vocabulary."
}}
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a strict but kind English language evaluator."},
                {"role": "user", "content": evaluation_prompt}
            ],
            temperature=0.3
        )
        eval_json = response.choices[0].message.content.strip()
        return json.loads(eval_json)
    except Exception as e:
        print(f"[❌ Evaluation Error]: {e}")
        return {
            "score": "0%",
            "feedback": "Evaluation failed.",
            "suggestions": [],
            "remarks": "Please try again later."
        }

