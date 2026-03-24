from fastapi import APIRouter
from models.request_models import Question
from services.ai_service import generate_answer
from services.supabase_client import supabase

router = APIRouter()
@router.post("/ask")
def ask_question(data: Question):

    answer = generate_answer(data.question, data.session_id)

    if data.user_id:
        supabase.table("chat_history").insert({
            "user_id": data.user_id,
            "session_id": data.session_id,  # 🔥 ADD THIS
            "question": data.question,
            "answer": answer
        }).execute()

    return {"answer": answer}

@router.get("/chat-history/{user_id}")
def get_chat_history(user_id: str):

    response = supabase.table("chat_history") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("created_at") \
        .execute()

    return response.data