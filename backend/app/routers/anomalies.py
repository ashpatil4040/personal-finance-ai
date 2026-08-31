from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..anomalies import detect_anomalies
from ..auth import get_current_user
from ..database import get_db
from ..models import User

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


@router.get("", response_model=schemas.AnomaliesResponse)
def list_anomalies(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return detect_anomalies(db, current.id)
