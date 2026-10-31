from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import llm, schemas
from ..auth import get_current_user
from ..categorize import categorize_batch
from ..database import get_db
from ..ingest import CSVParseError, parse_csv
from ..models import Account, Statement, Transaction, User
from ..pdf_ingest import extract_text, parse_pdf_heuristic

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


def _parse_csv(content: bytes) -> tuple[list[dict], str]:
    try:
        return parse_csv(content), "csv"
    except CSVParseError:
        text = content.decode("utf-8-sig", errors="replace")
        if len(text) <= 12000:
            rows = llm.extract_transactions_from_text(text)
            if rows:
                return rows, "csv-llm"
        raise


def _extract_rows(filename: str, content: bytes) -> tuple[list[dict], str]:
    """Return (rows, method) for a supported statement file.

    CSV uses the deterministic parser. PDF tries table/text heuristics first and
    falls back to the LLM extractor when configured and the heuristics come up
    empty. Raises CSVParseError (400) when nothing usable can be extracted.
    """
    name = filename.lower()
    if name.endswith(".csv"):
        return _parse_csv(content)

    if name.endswith(".pdf"):
        rows = parse_pdf_heuristic(content)
        if rows:
            return rows, "pdf-heuristic"
        if not llm.llm_available():
            raise CSVParseError(
                "Local PDF parsing found no transactions, and AI extraction "
                "isn't available. Check PFAI_LLM_ENABLED and the OpenAI API key."
            )
        text = extract_text(content)
        if not text.strip():
            raise CSVParseError(
                "This PDF contains no selectable text. Scanned/image-only PDFs "
                "aren't supported yet; try a text-based PDF or CSV export."
            )
        rows = llm.extract_transactions_from_text(text)
        if rows:
            return rows, "pdf-llm"
        raise CSVParseError(
            "AI extraction couldn't find transactions in the PDF text. Check "
            "the backend log for a safe OpenAI error summary, or try a CSV export."
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

    # One categorization pass for the whole statement (single LLM call when on).
    categories = categorize_batch(rows)
    for row, category in zip(rows, categories):
        db.add(
            Transaction(
                user_id=current.id,
                account_id=account_id,
                statement_id=statement.id,
                date=row["date"],
                description=row["description"],
                amount=row["amount"],
                category=category,
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
