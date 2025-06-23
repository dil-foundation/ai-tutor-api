import fitz  # PyMuPDF
import re
from typing import List
from app.schemas.pdf_quiz import QuizItem

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    doc = fitz.open(file_path)
    for page in doc:
        text += page.get_text()
    print("---- Extracted PDF Text ----\n", text) 
    return text

def parse_questions_from_text(text: str) -> dict:
    lines = text.strip().splitlines()

    # Title is the first non-empty line
    title = None
    for line in lines:
        if line.strip():
            title = line.strip()
            break

    # Rejoin text excluding title
    remaining_text = "\n".join(lines[1:]) if title else text

    # Split each question block
    question_blocks = re.split(r"\n(?=\d+\.)", remaining_text.strip())

    questions = []

    for block in question_blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue

        # Question line
        question_line = lines[0].strip()
        question_text = re.sub(r"^\d+\.\s*", "", question_line)

        options = []
        answer_text = None

        for i, line in enumerate(lines[1:]):
            line = line.strip()

            option_match = re.match(r"^[A-D]\)\s*(.+)", line)
            if option_match:
                options.append(option_match.group(1).strip())
                continue

            answer_match = re.match(r"^Ans:\s*(.+)", line, re.IGNORECASE)
            if answer_match:
                answer_text = answer_match.group(1).strip()
                continue

            # Fallback: any extra line after options as potential answer
            if i >= 4 and not answer_text and line:
                answer_text = line.strip()

        if len(options) < 2:
            continue

        quiz_item = QuizItem(
            question=question_text,
            options=options,
            answer=answer_text
        )
        questions.append(quiz_item)

    return {
        "title": title,
        "questions": questions
    }
