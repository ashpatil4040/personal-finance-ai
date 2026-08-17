from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..categorize import categorize
from ..database import get_db
from ..models import Account, Transaction, User

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _owned_account_or_none(db: Session, user: User, account_id: int | None) -> int | None:
    if account_id is None:
        return None
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account.id


@router.get("", response_model=list[schemas.TransactionOut])
def list_transactions(
    account_id: int | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=500, le=2000),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).filter(Transaction.user_id == current.id)
    if account_id is not None:
        q = q.filter(Transaction.account_id == account_id)
    if category:
        q = q.filter(Transaction.category == category)
    return q.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit).all()


@router.post("", response_model=schemas.TransactionOut, status_code=201)
def create_transaction(
    payload: schemas.TransactionCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account_id = _owned_account_or_none(db, current, payload.account_id)
    txn = Transaction(
        user_id=current.id,
        account_id=account_id,
        date=payload.date,
        description=payload.description,
        amount=payload.amount,
        category=payload.category or categorize(payload.description, payload.amount),
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@router.delete("/{txn_id}", status_code=204)
def delete_transaction(
    txn_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = db.query(Transaction).filter(Transaction.id == txn_id, Transaction.user_id == current.id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(txn)
    db.commit()
    return None
