from fastapi import APIRouter
from pydantic import BaseModel

from services.grammar_service import grammar_check

router = APIRouter()

class GrammarRequest(BaseModel):
    text: str


@router.post("/grammar-check")
async def check_grammar(request: GrammarRequest):

    corrected_text = grammar_check(request.text)

    return {
        "original_text": request.text,
        "corrected_text": corrected_text
    }