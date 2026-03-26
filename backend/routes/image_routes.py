from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.ocr_service import extract_text
from services.ai_service import generate_text

router = APIRouter()

ALLOWED_TYPES = {
    "image/jpeg", "image/jpg", "image/png",
    "image/bmp", "image/webp", "application/pdf"
}

@router.post("/ask-from-image")
async def ask_from_image(
    file: UploadFile = File(...),
    question: str = Form(...)
):
    # ✅ Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Upload JPG, PNG, or PDF."
        )

    # ✅ Validate question
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # ✅ OCR extraction
    try:
        extracted_text = await extract_text(file)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")

    if not extracted_text or extracted_text.strip() == "":
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted. Make sure the image is clear."
        )

    # ✅ Strong, specific prompt
    prompt = f"""You are a smart and helpful homework assistant for students.

A student has uploaded an image or document. The text extracted from it is shown below.

---
EXTRACTED TEXT:
{extracted_text}
---

STUDENT'S QUESTION:
{question}

---
YOUR TASK:
- Read the extracted text carefully and answer based on it.
- If the text contains MCQ questions, answer each one and briefly explain why.
- If the text contains a diagram or concept (e.g. Docker, algorithm, circuit), explain it clearly and simply.
- If the text contains notes or definitions, summarize and explain them for the student.
- Use simple language a school or college student can understand.
- Use bullet points or numbered steps where helpful.
- Do NOT say "the teacher should explain" — YOU explain it directly right now.
- Do NOT ignore the extracted text — your entire answer must be based on it.

Your answer:
"""

    # ✅ Generate answer
    try:
        answer = generate_text(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

    return {
        "filename": file.filename,
        "extracted_text": extracted_text,
        "question": question,
        "answer": answer
    }