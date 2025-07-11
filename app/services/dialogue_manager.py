import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'functional_dialogue.json')

def get_prompt_by_id(dialogue_id: int) -> dict:
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        dialogues = json.load(f)
        return next((item for item in dialogues if item['id'] == dialogue_id), None)

def get_next_prompt_id(current_id: int) -> int:
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        dialogues = json.load(f)
        current_index = next((i for i, d in enumerate(dialogues) if d['id'] == current_id), None)
        if current_index is not None and current_index + 1 < len(dialogues):
            return dialogues[current_index + 1]['id']
    return None