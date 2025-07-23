"""
English Correction and Accent Detection Service

This service provides sophisticated English language correction and accent detection:
- Grammar and syntax correction
- Thick accent pattern recognition
- Natural language suggestions
- Friendly, constructive feedback
- Context-aware corrections

Uses OpenAI GPT-4 for advanced language understanding and correction.
"""

from openai import OpenAI
from app.config import OPENAI_API_KEY
import re
import json

client = OpenAI(api_key=OPENAI_API_KEY)

def correct_english_text(text: str) -> dict:
    """
    Correct English text for grammar, syntax, and naturalness.
    Returns structured feedback with corrections and explanations.
    
    Args:
        text (str): The English text to correct
        
    Returns:
        dict: {
            "has_grammar_issues": bool,
            "corrected_text": str,
            "feedback": str,
            "issues": list,
            "confidence": float
        }
    """
    
    prompt = f"""
You are an expert English tutor specializing in helping non-native speakers improve their English.

Your task is to analyze the given English text and provide corrections for:
1. Grammar errors
2. Syntax issues
3. Unnatural phrasing
4. Word choice improvements
5. Sentence structure

Text to analyze: "{text}"

Please provide your response in the following JSON format:
{{
    "has_grammar_issues": true/false,
    "corrected_text": "the corrected version",
    "feedback": "friendly, constructive feedback explaining the corrections",
    "issues": ["list of specific issues found"],
    "confidence": 0.95
}}

Guidelines:
- Be encouraging and constructive in your feedback
- Focus on the most important corrections
- Provide natural, conversational English
- Consider context and meaning preservation
- Use simple, clear explanations
- Maintain a friendly, supportive tone

If the text is already correct and natural, set has_grammar_issues to false and provide positive reinforcement.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )

        result_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON from response
        try:
            # Find JSON content in the response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(result_text)
        except json.JSONDecodeError:
            # Fallback parsing
            print(f"Failed to parse JSON response: {result_text}")
            result = {
                "has_grammar_issues": True,
                "corrected_text": text,
                "feedback": "I noticed some areas for improvement. Let me help you with that.",
                "issues": ["Parsing error"],
                "confidence": 0.5
            }

        # Validate required fields
        required_fields = ["has_grammar_issues", "corrected_text", "feedback"]
        for field in required_fields:
            if field not in result:
                result[field] = "" if field == "feedback" else (False if field == "has_grammar_issues" else text)

        print(f"✅ English correction completed for: '{text}'")
        print(f"📝 Corrected: '{result.get('corrected_text', text)}'")
        print(f"🔍 Has issues: {result.get('has_grammar_issues', False)}")
        
        return result

    except Exception as e:
        print(f"❌ Error in English correction: {str(e)}")
        return {
            "has_grammar_issues": True,
            "corrected_text": text,
            "feedback": "I noticed some areas for improvement. Let me help you with that.",
            "issues": [f"Error: {str(e)}"],
            "confidence": 0.0
        }

def detect_accent_issues(text: str) -> dict:
    """
    Detect thick accent patterns and provide pronunciation guidance.
    Focuses on common accent issues from Urdu/Hindi speakers.
    
    Args:
        text (str): The English text to analyze for accent patterns
        
    Returns:
        dict: {
            "has_accent_issues": bool,
            "accent_patterns": list,
            "feedback": str,
            "pronunciation_tips": list,
            "confidence": float
        }
    """
    
    prompt = f"""
You are an expert accent coach specializing in helping Urdu/Hindi speakers improve their English pronunciation.

Your task is to analyze the given English text and identify potential accent issues that are common among Urdu/Hindi speakers, such as:
1. "How much time" instead of "how long"
2. "I am going to home" instead of "I am going home"
3. "Please tell me" instead of "could you tell me"
4. "I am having" instead of "I have"
5. "Do one thing" instead of "here's what we can do"
6. "Kindly" overuse
7. "Actually" overuse
8. Direct translations from Urdu/Hindi

Text to analyze: "{text}"

Please provide your response in the following JSON format:
{{
    "has_accent_issues": true/false,
    "accent_patterns": ["list of detected accent patterns"],
    "feedback": "friendly feedback about accent patterns",
    "pronunciation_tips": ["specific tips for improvement"],
    "confidence": 0.95
}}

Guidelines:
- Be encouraging and supportive
- Focus on the most common accent patterns
- Provide specific, actionable advice
- Consider cultural context
- Use gentle, constructive language
- Highlight both issues and strengths

If no accent issues are detected, set has_accent_issues to false and provide positive reinforcement.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )

        result_text = response.choices[0].message.content.strip()
        
        # Try to extract JSON from response
        try:
            # Find JSON content in the response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(result_text)
        except json.JSONDecodeError:
            # Fallback parsing
            print(f"Failed to parse JSON response: {result_text}")
            result = {
                "has_accent_issues": False,
                "accent_patterns": [],
                "feedback": "Your pronunciation sounds great!",
                "pronunciation_tips": [],
                "confidence": 0.5
            }

        # Validate required fields
        required_fields = ["has_accent_issues", "accent_patterns", "feedback", "pronunciation_tips"]
        for field in required_fields:
            if field not in result:
                if field == "has_accent_issues":
                    result[field] = False
                elif field in ["accent_patterns", "pronunciation_tips"]:
                    result[field] = []
                else:
                    result[field] = ""

        print(f"✅ Accent detection completed for: '{text}'")
        print(f"🎯 Has accent issues: {result.get('has_accent_issues', False)}")
        print(f"📋 Patterns: {result.get('accent_patterns', [])}")
        
        return result

    except Exception as e:
        print(f"❌ Error in accent detection: {str(e)}")
        return {
            "has_accent_issues": False,
            "accent_patterns": [],
            "feedback": "Your pronunciation sounds great!",
            "pronunciation_tips": [],
            "confidence": 0.0
        }

def analyze_english_input(text: str) -> dict:
    """
    Comprehensive analysis of English input combining grammar and accent detection.
    
    Args:
        text (str): The English text to analyze
        
    Returns:
        dict: Combined analysis results
    """
    
    # Run both analyses in parallel (in a real implementation, you might want to use async)
    grammar_result = correct_english_text(text)
    accent_result = detect_accent_issues(text)
    
    # Combine results
    combined_result = {
        "original_text": text,
        "grammar_analysis": grammar_result,
        "accent_analysis": accent_result,
        "overall_issues": grammar_result.get("has_grammar_issues", False) or accent_result.get("has_accent_issues", False),
        "combined_feedback": ""
    }
    
    # Generate combined feedback
    feedback_parts = []
    
    if grammar_result.get("has_grammar_issues", False):
        feedback_parts.append(grammar_result.get("feedback", ""))
    
    if accent_result.get("has_accent_issues", False):
        feedback_parts.append(accent_result.get("feedback", ""))
    
    if not feedback_parts:
        feedback_parts.append("Excellent! Your English sounds natural and correct.")
    
    combined_result["combined_feedback"] = " ".join(feedback_parts)
    
    return combined_result

def get_pronunciation_guide(word: str) -> dict:
    """
    Get pronunciation guide for specific words.
    
    Args:
        word (str): The word to get pronunciation for
        
    Returns:
        dict: Pronunciation information
    """
    
    prompt = f"""
Provide a pronunciation guide for the word: "{word}"

Include:
1. Phonetic spelling
2. Common mispronunciations
3. Tips for correct pronunciation
4. Audio cues if helpful

Format as JSON:
{{
    "word": "{word}",
    "phonetic": "phonetic spelling",
    "common_mistakes": ["list of common mistakes"],
    "tips": ["pronunciation tips"],
    "audio_cues": "helpful audio cues"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )

        result_text = response.choices[0].message.content.strip()
        
        try:
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(result_text)
        except json.JSONDecodeError:
            result = {
                "word": word,
                "phonetic": word,
                "common_mistakes": [],
                "tips": ["Practice saying this word slowly"],
                "audio_cues": "Listen to native speakers"
            }

        return result

    except Exception as e:
        print(f"❌ Error in pronunciation guide: {str(e)}")
        return {
            "word": word,
            "phonetic": word,
            "common_mistakes": [],
            "tips": ["Practice saying this word slowly"],
            "audio_cues": "Listen to native speakers"
        } 