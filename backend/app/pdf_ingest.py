"""PDF statement parsing (Phase 2).

Two strategies, in order:
1. Table extraction via pdfplumber (works well for statements rendered with a
   gridded table).
2. Line-by-line text heuristics: find a date and a trailing amount on each line.

Both return normalized rows: {date, description, amount} with the same amount
convention as the CSV path (negative = spending, positive = income). When these
heuristics come up short, the caller can fall back to LLM extraction
(``app.llm``) if it is configured.
"""

from __future__ import annotations

import io
import re
from datetime import date

import pdfplumber

from .ingest import _to_float  # reuse the shared money parser

# Matches ISO (2026-08-01), US (08/01/2026 or 8/1/26), and "Aug 1, 2026".
_DATE_PATTERNS = [
    (re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"), ["%Y-%m-%d"]),
    (re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b"), ["%m/%d/%Y", "%m/%d/%y"]),
    (
        re.compile(
            r"\b([A-Z][a-z]{2,8}\.?\s+\d{1,2},?\s+\d{4})\b"
        ),
        ["%b %d %Y", "%b %d, %Y", "%B %d %Y", "%B %d, %Y"],
    ),
]

# A money token like 1,234.56 or (1,234.56) or $-42.10, anchored to line end.
_AMOUNT_RE = re.compile(r"(-?\(?\$?-?[\d,]+\.\d{2}\)?)\s*$")


def extract_text(content: bytes) -> str:
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _parse_date(token: str):
    from datetime import datetime

    token = token.strip().replace(".", "")
    for pattern, fmts in _DATE_PATTERNS:
        m = pattern.search(token)
        if not m:
            continue
        raw = m.group(1).replace(".", "").replace(",", "")
        for fmt in fmts:
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return None


def _rows_from_tables(content: bytes) -> list[dict]:
    from .ingest import (
        AMOUNT_ALIASES,
        CREDIT_ALIASES,
        DATE_ALIASES,
        DEBIT_ALIASES,
        DESC_ALIASES,
        _find,
    )

    rows: list[dict] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                header = [str(c or "").strip().lower() for c in table[0]]
                colmap = {name: idx for idx, name in enumerate(header) if name}
                date_i = _find(colmap, DATE_ALIASES)
                desc_i = _find(colmap, DESC_ALIASES)
                amt_i = _find(colmap, AMOUNT_ALIASES)
                debit_i = _find(colmap, DEBIT_ALIASES)
                credit_i = _find(colmap, CREDIT_ALIASES)
                if date_i is None or desc_i is None:
                    continue
                for raw in table[1:]:
                    if not raw:
                        continue
                    d = _parse_date(str(raw[date_i])) if date_i is not None and date_i < len(raw) else None
                    if not d:
                        continue
                    description = str(raw[desc_i]).strip() if desc_i < len(raw) else ""
                    if amt_i is not None and amt_i < len(raw):
                        amount = _to_float(raw[amt_i])
                    else:
                        debit = _to_float(raw[debit_i]) if debit_i is not None and debit_i < len(raw) else None
                        credit = _to_float(raw[credit_i]) if credit_i is not None and credit_i < len(raw) else None
                        amount = (abs(credit) if credit else 0.0) - (abs(debit) if debit else 0.0)
                    if amount is None:
                        continue
                    rows.append(
                        {
                            "date": d,
                            "description": (description or "(no description)")[:255],
                            "amount": round(float(amount), 2),
                        }
                    )
    return rows


def _rows_from_text(content: bytes) -> list[dict]:
    rows: list[dict] = []
    text = extract_text(content)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        d = _parse_date(line)
        if not d:
            continue
        m = _AMOUNT_RE.search(line)
        if not m:
            continue
        amount = _to_float(m.group(1))
        if amount is None:
            continue
        # Description = line minus the leading date token and trailing amount.
        desc = line[: m.start()]
        for pattern, _ in _DATE_PATTERNS:
            desc = pattern.sub("", desc, count=1)
        desc = desc.strip(" \t-|") or "(no description)"
        rows.append({"date": d, "description": desc[:255], "amount": round(float(amount), 2)})
    return rows


def parse_pdf_heuristic(content: bytes) -> list[dict]:
    """Best-effort heuristic parse. Returns [] when nothing usable is found."""
    rows = _rows_from_tables(content)
    if rows:
        return rows
    return _rows_from_text(content)
