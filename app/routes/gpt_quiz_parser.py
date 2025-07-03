from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.gpt_parser import extract_quiz_from_text_using_gpt
from app.schemas.pdf_quiz import PDFUrlRequest, QuizResponse
import fitz  # PyMuPDF
import requests
import tempfile
import os

router = APIRouter()

def extract_text_by_page(file_path: str) -> str:
    doc = fitz.open(file_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    return full_text.strip()


@router.post(
    "/ai-based-quiz-from-pdf-upload",
    response_model=QuizResponse,
    summary="Upload a PDF and extract quiz",
    description="This endpoint accepts a PDF file uploaded by the user, extracts the text, and  then sends the text to GPT to extract a quiz with questions and answers from the extracted text from the pdf. The output includes a title (if available) and a list of questions with options.",
    tags=["AI Based Quiz Parser"]
)
async def upload_pdf_for_gpt_quiz(file: UploadFile = File(...)):
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as f:
        f.write(await file.read())

    text = extract_text_by_page(temp_file_path)

    # Print the extracted text
    print("Extracted PDF Text:\n", text)

    result = extract_quiz_from_text_using_gpt(text)

    return result

@router.post(
    "/ai-based-quiz-from-url",
    response_model=QuizResponse,
    summary="Extract quiz from a PDF via URL",
    description="This endpoint accepts a PDF link (e.g., S3 URL), downloads the file, extracts text using PyMuPDF, and then sends the text to GPT to extract a quiz with questions and answers from the extracted text from the pdf",
    tags=["AI Based Quiz Parser"]
)
async def upload_pdf_from_url_for_gpt_quiz(request: PDFUrlRequest):
    try:
        response = requests.get(request.url, stream=True)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download the PDF file from the URL.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp_path = tmp.name

        text = extract_text_by_page(tmp_path)
        print("Extracted PDF Text from URL:\n", text)

        result = extract_quiz_from_text_using_gpt(text)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
