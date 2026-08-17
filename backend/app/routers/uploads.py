from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..categorize import categorize
from ..database import get_db
from ..ingest import CSVParseError, parse_csv
from ..models import Account, Statement, Transaction, User

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("", response_model=schemas.UploadResult, status_code=201)
async def upload_statement(
    file: UploadFile = File(...),
    account_id: int | None = Form(default=None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported in Phase 1.")

    if account_id is not None:
        owned = db.query(Account).filter(Account.id == account_id, Account.user_id == current.id).first()
        if not owned:
            raise HTTPException(status_code=404, detail="Account not found")

    content = await file.read()
    try:
        rows = parse_csv(content)
    except CSVParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    statement = Statement(
        user_id=current.id,
        account_id=account_id,
        filename=file.filename or "upload.csv",
        row_count=len(rows),
        status="parsed",
    )
    db.add(statement)
    db.flush()  # get statement.id

    for row in rows:
        db.add(
            Transaction(
                user_id=current.id,
                account_id=account_id,
                statement_id=statement.id,
                date=row["date"],
                description=row["description"],
                amount=row["amount"],
                category=categorize(row["description"], row["amount"]),
            )
        )
    db.commit()
    db.refresh(statement)

    return schemas.UploadResult(
        statement_id=statement.id,
        filename=statement.filename,
        imported=len(rows),
        account_id=account_id,
    )
