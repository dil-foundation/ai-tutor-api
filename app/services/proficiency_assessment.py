import os
from openai import OpenAI
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def assess_english_proficiency(text: str) -> int:
    """
    Assesses the user's English proficiency based on the provided text and assigns a starting stage.

    Args:
        text: The text provided by the user during sign-up.

    Returns:
        An integer representing the assigned stage (0-3).
        Returns 0 as a fallback if the assessment fails.
    """
    if not text or not text.strip():
        logger.warning("Proficiency text is empty. Assigning stage 0 by default.")
        return 0

    try:
        logger.info(f"Assessing proficiency for text: '{text}'")
        
        system_prompt = """
        You are an expert English language proficiency evaluator. Your task is to assess a user's 
        self-described English proficiency and assign them a starting stage from 0 to 6.
        The stages are defined as follows:
        - Stage 0 (A1): Absolute beginner, knows only a few words or simple phrases. For users who write "I don't know English" or similar.
        - Stage 1 (A1/A2): Foundation Speaking. Can handle basic conversation skills and pronunciation.
        - Stage 2 (A2): Daily Communication. Can handle practical daily life conversations and routine expressions.
        - Stage 3 (B1): Storytelling & Discussion. Has narrative skills and can participate in group discussions.
        - Stage 4 (B2): Professional Communication. Can handle business and professional communication.
        - Stage 5 (C1): Advanced Debate & Analysis. Can handle complex argumentation and academic presentations.
        - Stage 6 (C2): Mastery & Diplomacy. Can use language flexibly and spontaneously for all purposes.

        Analyze the provided text for grammatical accuracy, vocabulary range, sentence structure, and overall coherence.
        Based on your analysis, return a single integer for the most appropriate starting stage.
        Your response MUST be a valid JSON object with a single key "assigned_stage". For example: {"assigned_stage": 2}
        """

        evaluation_prompt = f"Please evaluate the following text and assign a starting stage:\n\n---\n{text}\n---"

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": evaluation_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=50
        )

        response_content = response.choices[0].message.content
        logger.info(f"OpenAI response received: {response_content}")

        if response_content:
            data = json.loads(response_content)
            assigned_stage = data.get("assigned_stage")

            if isinstance(assigned_stage, int) and 0 <= assigned_stage <= 6:
                logger.info(f"Successfully assigned stage: {assigned_stage}")
                return assigned_stage
            else:
                logger.error(f"Invalid stage '{assigned_stage}' in OpenAI response. Defaulting to stage 0.")
                return 0
        else:
            logger.error("Empty response from OpenAI. Defaulting to stage 0.")
            return 0

    except Exception as e:
        logger.error(f"An error occurred during proficiency assessment: {str(e)}")
        # In case of any failure (API error, parsing error, etc.), default to the safest stage.
        return 0
