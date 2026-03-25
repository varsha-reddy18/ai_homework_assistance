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

    answer = generate_answer(
        data.question,
        data.session_id,
        data.subject
    )

    return {"answer": answer}