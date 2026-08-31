from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import llm, schemas
from ..agent import answer_question
from ..auth import get_current_user
from ..database import get_db
from ..models import User

router = APIRouter(prefix="/api/ask", tags=["ask"])


@router.post("", response_model=schemas.AskResponse)
def ask(
    payload: schemas.AskRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not llm.llm_available():
        return schemas.AskResponse(
            answer=(
                "The AI assistant isn't configured yet. Set PFAI_LLM_ENABLED=true "
                "and an OPENAI_API_KEY to ask questions about your finances."
            ),
            tools_used=[],
            grounded=False,
        )

    try:
        result = answer_question(db, current.id, payload.question)
    except Exception:  # noqa: BLE001 - surface a friendly message, never 500
        return schemas.AskResponse(
            answer="Sorry, I hit an error answering that. Please try rephrasing.",
            tools_used=[],
            grounded=False,
        )
    return schemas.AskResponse(answer=result["answer"], tools_used=result["tools_used"], grounded=True)
