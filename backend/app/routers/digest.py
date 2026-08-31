from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..digest import build_digest
from ..models import User

router = APIRouter(prefix="/api/digest", tags=["digest"])


@router.get("", response_model=schemas.DigestResponse)
def digest(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_digest(db, current.id)
