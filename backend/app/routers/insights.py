from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..categorize import generate_insights
from ..database import get_db
from ..models import Transaction, User

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("", response_model=schemas.InsightsResponse)
def insights(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txns = db.query(Transaction).filter(Transaction.user_id == current.id).all()
    return generate_insights(txns)
