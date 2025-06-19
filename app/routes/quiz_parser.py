from fastapi import APIRouter, UploadFile, File
import os
import requests
import tempfile
from app.services.pdf_parser import extract_text_from_pdf, parse_questions_from_text
from app.schemas.pdf_quiz import PDFUrlRequest, QuizResponse, QuizItem
from typing import List
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post(
    "/upload-quiz-from-url",
    response_model=QuizResponse,
    summary="Extract quiz questions from uploaded link - PDF"
)
async def upload_quiz_from_url(request: PDFUrlRequest):
    try:
        response = requests.get(request.url, stream=True)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download the PDF")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    tmp.write(chunk)
            tmp_path = tmp.name

        text = extract_text_from_pdf(tmp_path)
        result = parse_questions_from_text(text) 
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
