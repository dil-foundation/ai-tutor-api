import json
import uuid
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from app.config import OPENAI_API_KEY
from app.redis_client import get_redis_client, is_redis_available
import base64
from app.services.tts import synthesize_speech_exercises

client = OpenAI(api_key=OPENAI_API_KEY)

class RoleplayAgent:
    def __init__(self):
        self.scenarios = self._load_scenarios()
    
    def _load_scenarios(self) -> Dict:
        """Load roleplay scenarios from JSON file"""
        try:
            with open('app/data/roleplay_simulation.json', 'r', encoding='utf-8') as f:
                scenarios = json.load(f)
                return {scenario['id']: scenario for scenario in scenarios}
        except Exception as e:
            print(f"❌ [ROLEPLAY] Error loading scenarios: {str(e)}")
            return {}
    
    def get_scenario_by_id(self, scenario_id: int) -> Optional[Dict]:
        """Get scenario by ID"""
        return self.scenarios.get(scenario_id)
    
    def get_all_scenarios(self) -> List[Dict]:
        """Get all available scenarios"""
        return list(self.scenarios.values())
    
    def create_session(self, scenario: Dict) -> Tuple[str, str]:
        """Create a new roleplay session and return session ID and initial prompt"""
        session_id = f"roleplay_{uuid.uuid4().hex}"
        
        # Create initial conversation state
        initial_state = {
            "scenario_id": scenario["id"],
            "scenario_context": scenario["scenario_context"],
            "ai_character": scenario["ai_character"],
            "expected_keywords": scenario["expected_keywords"],
            "conversation_flow": scenario["conversation_flow"],
            "cultural_context": scenario["cultural_context"],
            "history": [
                {
                    "role": "assistant",
                    "content": scenario["initial_prompt"],
                    "timestamp": "initial"
                }
            ],
            "current_turn": "user",
            "session_started": True
        }
        
        # Store in Redis
        redis_client = get_redis_client()
        if redis_client:
            redis_client.setex(session_id, 3600, json.dumps(initial_state))  # 1 hour expiry
        else:
            print("⚠️ [ROLEPLAY] Redis not available, session state not persisted")
        
        print(f"✅ [ROLEPLAY] Created session {session_id} for scenario {scenario['id']}")
        return session_id, scenario["initial_prompt"]
    
    def update_session(self, session_id: str, user_input: str) -> Tuple[str, str, Optional[str]]:
        """Update session with user input and return AI response"""
        try:
            # Get session data from Redis
            redis_client = get_redis_client()
            if not redis_client:
                print("⚠️ [ROLEPLAY] Redis not available, cannot retrieve session")
                return "I'm sorry, but I can't continue our conversation right now. Please start a new session.", "error", None
            
            session_data_json = redis_client.get(session_id)
            if not session_data_json:
                return "", "error", "Session not found"
            
            session_data = json.loads(session_data_json)
            scenario = self.get_scenario_by_id(session_data["scenario_id"])
            if not scenario:
                return "", "error", "Scenario not found"
            
            # Add user message to history
            session_data["history"].append({
                "role": "user",
                "content": user_input,
                "timestamp": "user_input"
            })
            
            # Generate AI response
            ai_response = self._generate_ai_response(session_data, user_input, scenario)
            
            # Add AI response to history
            session_data["history"].append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": "ai_response"
            })
            
            # Check if conversation should end
            conversation_status = self._check_conversation_end(session_data, ai_response)
            
            # Update session in Redis
            redis_client = get_redis_client()
            if redis_client:
                redis_client.setex(session_id, 3600, json.dumps(session_data))
            else:
                print("⚠️ [ROLEPLAY] Redis not available, session state not persisted")
            
            print(f"✅ [ROLEPLAY] Updated session {session_id}, status: {conversation_status}")
            return ai_response, conversation_status, None
            
        except Exception as e:
            print(f"❌ [ROLEPLAY] Error updating session: {str(e)}")
            return "", "error", str(e)
    
    def _generate_ai_response(self, session_data: Dict, user_input: str, scenario: Dict) -> str:
        """Generate AI response based on scenario context and conversation history"""
        try:
            # Create context-aware prompt
            prompt = f"""
You are roleplaying as a {scenario['ai_character']} in a {scenario['scenario_context']} scenario.
Cultural context: {scenario['cultural_context']}
Conversation flow: {scenario['conversation_flow']}

Your role: {scenario['ai_character']}
Expected keywords for the student to use: {', '.join(scenario['expected_keywords'])}

Previous conversation:
{self._format_conversation_history(session_data['history'])}

Student's latest response: "{user_input}"

Respond naturally as the {scenario['ai_character']}, keeping the conversation flowing.
Your response should:
1. Be appropriate for the scenario and your character
2. Encourage the student to use the expected keywords naturally
3. Keep the conversation engaging and realistic
4. Be 1-2 sentences maximum
5. Maintain the cultural context of {scenario['cultural_context']}

Respond as the {scenario['ai_character']}:
"""
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a {scenario['ai_character']} in a {scenario['scenario_context']} scenario. Stay in character and keep responses natural and engaging."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            ai_response = response.choices[0].message.content.strip()
            print(f"✅ [ROLEPLAY] Generated AI response: {ai_response}")
            return ai_response
            
        except Exception as e:
            print(f"❌ [ROLEPLAY] Error generating AI response: {str(e)}")
            return "I'm sorry, could you please repeat that?"
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history for AI prompt"""
        formatted = ""
        for message in history[-6:]:  # Last 6 messages for context
            role = "Student" if message["role"] == "user" else "AI"
            formatted += f"{role}: {message['content']}\n"
        return formatted
    
    def _check_conversation_end(self, session_data: Dict, ai_response: str) -> str:
        """Check if the conversation should end naturally"""
        # Simple logic: end after 8-12 exchanges or if AI indicates completion
        message_count = len(session_data["history"])
        
        if message_count >= 20:  # Maximum conversation length
            return "end"
        
        # Check if AI response indicates conversation completion
        end_indicators = [
            "thank you", "goodbye", "have a nice day", "see you", 
            "that's all", "anything else", "is there anything else"
        ]
        
        if any(indicator in ai_response.lower() for indicator in end_indicators):
            return "end"
        
        return "continue"
    
    def get_session_history(self, session_id: str) -> Optional[List[Dict]]:
        """Get conversation history for a session"""
        try:
            redis_client = get_redis_client()
            if not redis_client:
                print("⚠️ [ROLEPLAY] Redis not available, cannot retrieve session history")
                return None
            
            session_data_json = redis_client.get(session_id)
            if not session_data_json:
                return None
            
            session_data = json.loads(session_data_json)
            return session_data.get("history", [])
            
        except Exception as e:
            print(f"❌ [ROLEPLAY] Error getting session history: {str(e)}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session from Redis"""
        try:
            redis_client = get_redis_client()
            if redis_client:
                redis_client.delete(session_id)
                print(f"✅ [ROLEPLAY] Deleted session {session_id}")
                return True
            else:
                print("⚠️ [ROLEPLAY] Redis not available, cannot delete session")
                return False
        except Exception as e:
            print(f"❌ [ROLEPLAY] Error deleting session: {str(e)}")
            return False
    
    async def generate_audio_for_response(self, text: str) -> Optional[bytes]:
        """Generate audio for AI response"""
        try:
            audio_content = await synthesize_speech_exercises(text)
            return audio_content
        except Exception as e:
            print(f"❌ [ROLEPLAY] Error generating audio: {str(e)}")
            return None

# Global instance
roleplay_agent = RoleplayAgent() 