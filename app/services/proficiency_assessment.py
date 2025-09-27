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
    Assesses the user's ACTUAL English proficiency level based on their written text and assigns a starting stage.

    This function analyzes the user's demonstrated English knowledge through their writing, focusing on:
    - Grammar accuracy and complexity
    - Vocabulary range and sophistication  
    - Sentence structure variety
    - Overall fluency and coherence
    - Error patterns and frequency

    Args:
        text: The text written by the user during sign-up (acts as a proficiency test).

    Returns:
        An integer representing the assigned stage (0-6) based on demonstrated English knowledge.
        Returns 0 as a fallback if the assessment fails.
    """
    if not text or not text.strip():
        logger.warning("Proficiency text is empty. Assigning stage 0 by default.")
        return 0

    try:
        logger.info(f"Assessing proficiency for text: '{text}'")
        
        system_prompt = """
        You are an expert English language proficiency evaluator. Your task is to assess a user's ACTUAL English proficiency level based on the text they have written and assign them an appropriate starting stage from 0 to 6.

        IMPORTANT: Focus on analyzing the user's DEMONSTRATED English knowledge, not their self-description. Evaluate their actual language skills shown in the text.

        The stages are defined as follows:
        - Stage 0 (A1): Basic vocabulary, simple sentences, frequent errors, limited grammar knowledge
        - Stage 1 (A1/A2): Simple present/past tense, basic vocabulary, some sentence variety, common errors
        - Stage 2 (A2): Present/past/future tenses, expanded vocabulary, compound sentences, fewer errors
        - Stage 3 (B1): Complex sentences, varied tenses, good vocabulary range, minimal errors, narrative ability
        - Stage 4 (B2): Advanced grammar, sophisticated vocabulary, complex structures, professional language
        - Stage 5 (C1): Near-native fluency, academic language, complex argumentation, minimal errors
        - Stage 6 (C2): Native-like proficiency, idiomatic expressions, perfect grammar, sophisticated style

        EVALUATION CRITERIA:
        1. Grammar accuracy and complexity
        2. Vocabulary range and sophistication
        3. Sentence structure variety
        4. Overall coherence and fluency
        5. Error frequency and types
        6. Language complexity demonstrated

        Analyze the provided text for these criteria and assign the most appropriate stage based on the user's ACTUAL English knowledge demonstrated in their writing.

        Your response MUST be a valid JSON object with a single key "assigned_stage". For example: {"assigned_stage": 3}
        """

        evaluation_prompt = f"""Analyze the following text and assess the user's English proficiency level based on their demonstrated language skills:

Text to evaluate:
---
{text}
---

Consider the following aspects:
- Grammar accuracy and complexity
- Vocabulary sophistication and range
- Sentence structure variety
- Overall fluency and coherence
- Error patterns and frequency

Assign a stage (0-6) based on the ACTUAL English knowledge demonstrated in this text."""

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
