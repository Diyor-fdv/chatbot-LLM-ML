from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatAskRequest, ChatAskResponse
from app.services.chat_service import answer_question

router = APIRouter()


@router.post("/ask", response_model=ChatAskResponse)
def ask(req: ChatAskRequest, db: Session = Depends(get_db)) -> ChatAskResponse:
    return answer_question(db, question=req.question, context=req.context)

