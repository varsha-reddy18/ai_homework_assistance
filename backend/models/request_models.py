from pydantic import BaseModel
from typing import Optional, List

# -----------------------
# USER QUESTION (CHAT

class Question(BaseModel):
    question: str
    user_id: str | None = None
    session_id: str | None = None
    subject: str | None = None   # ✅ ADD THIS        


class AnswerResponse(BaseModel):
    answer: str
    session_id: Optional[str] = None


# -----------------------
# IMAGE OCR RESPONSE
# -----------------------
class ImageResponse(BaseModel):
    extracted_question: str
    answer: str
    user_id: Optional[str] = None


# -----------------------
# CHAT HISTORY (OPTIONAL)
# -----------------------
class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatHistory(BaseModel):
    session_id: str
    messages: List[ChatMessage]