from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import llm, schemas
from ..auth import get_current_user
from ..categorize import categorize
from ..database import get_db
from ..ingest import CSVParseError, parse_csv
from ..models import Account, Statement, Transaction, User
from ..pdf_ingest import extract_text, parse_pdf_heuristic

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


def _extract_rows(filename: str, content: bytes) -> tuple[list[dict], str]:
    """Return (rows, method) for a supported statement file.

    CSV uses the deterministic parser. PDF tries table/text heuristics first and
    falls back to the LLM extractor when configured and the heuristics come up
    empty. Raises CSVParseError (400) when nothing usable can be extracted.
    """
    name = filename.lower()
    if name.endswith(".csv"):
        return parse_csv(content), "csv"

    if name.endswith(".pdf"):
        rows = parse_pdf_heuristic(content)
        if rows:
            return rows, "pdf-heuristic"
        # Heuristics failed — try the LLM fallback if it's turned on.
        if llm.llm_available():
            rows = llm.extract_transactions_from_text(extract_text(content))
            if rows:
                return rows, "pdf-llm"
        raise CSVParseError(
            "Could not read transactions from this PDF. If it is an unusual "
            "format, enable AI extraction (set PFAI_LLM_ENABLED with AWS Bedrock "
            "credentials) and try again."
        )

    raise CSVParseError("Unsupported file type. Upload a .csv or .pdf statement.")


@router.post("", response_model=schemas.UploadResult, status_code=201)
async def upload_statement(
    file: UploadFile = File(...),
    account_id: int | None = Form(default=None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    name = (file.filename or "").lower()
    if not (name.endswith(".csv") or name.endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Only .csv and .pdf files are supported.")

    if account_id is not None:
        owned = db.query(Account).filter(Account.id == account_id, Account.user_id == current.id).first()
        if not owned:
            raise HTTPException(status_code=404, detail="Account not found")

    content = await file.read()
    try:
        rows, method = _extract_rows(file.filename or "upload", content)
    except CSVParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    statement = Statement(
        user_id=current.id,
        account_id=account_id,
        filename=file.filename or "upload",
        row_count=len(rows),
        status=method,
    )
    db.add(statement)
    db.flush()

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
        method=method,
    )
