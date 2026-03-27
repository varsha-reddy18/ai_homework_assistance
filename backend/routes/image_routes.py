from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from services.ocr_service import extract_text
from services.doc_answering import answer_from_document   # ✅ new smart module

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
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Upload JPG, PNG, or PDF."
        )

    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        extracted_text = await extract_text(file)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")

    if not extracted_text or extracted_text.strip() == "":
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted. Make sure the image/PDF is clear."
        )

    # ✅ Smart document answering (no flan-t5 for this)
    answer = answer_from_document(question=question, document_text=extracted_text)

    return {
        "filename": file.filename,
        "extracted_text": extracted_text,
        "question": question,
        "answer": answer
    }