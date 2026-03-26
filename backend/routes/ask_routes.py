from fastapi import APIRouter
from pydantic import BaseModel
from services.ai_service import generate_answer

router = APIRouter()

# -----------------------
# REQUEST MODEL
# -----------------------
class Question(BaseModel):
    question: str
    subject: str = "General"
    session_id: str = "default"
    user_id: str | None = None

# -----------------------
# ASK ROUTE
# -----------------------
@router.post("/ask")
def ask_question(data: Question):

    # Pass the question text directly (no cleaning) to preserve Telugu/Hindi characters
    answer = generate_answer(
        question=data.question.strip(),  # keep original text
        session_id=data.session_id,
        subject=data.subject
    )

    return {"answer": answer}