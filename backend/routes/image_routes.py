from fastapi import APIRouter, UploadFile, File, Form
from services.ocr_service import extract_text
from services.ai_service import generate_text

router = APIRouter()

@router.post("/ask-from-image")
async def ask_from_image(
    file: UploadFile = File(...),
    question: str = Form(...)
):

    # OCR extract
    extracted_text = extract_text(file)

    # AI prompt
    prompt = f"""
You are a helpful teacher.

Use the following text extracted from a student's homework image.

Text:
{extracted_text}

Question:
{question}

Answer clearly for students.
"""

    answer = generate_text(prompt)

    return {
        "extracted_text": extracted_text,
        "answer": answer
    }