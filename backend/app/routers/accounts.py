from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import Account, User

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[schemas.AccountOut])
def list_accounts(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Account)
        .filter(Account.user_id == current.id)
        .order_by(Account.created_at.asc())
        .all()
    )


@router.post("", response_model=schemas.AccountOut, status_code=201)
def create_account(
    payload: schemas.AccountCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = Account(
        user_id=current.id,
        name=payload.name,
        type=payload.type,
        institution=payload.institution,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
