"""CSV statement parsing and normalization (Phase 1).

Accepts common bank/credit-card CSV exports with flexible column names and
normalizes them to (date, description, amount) rows. Amount convention:
positive = income, negative = spending. Supports either a single signed
``amount`` column or separate debit/credit columns.
"""

from __future__ import annotations

import io
import re
from datetime import date

import pandas as pd

DATE_ALIASES = [
    "date", "transaction date", "posted date", "posting date", "post date",
    "trans date", "purchase date", "effective date", "process date",
]
DESC_ALIASES = [
    "description", "transaction description", "transaction details", "details",
    "memo", "name", "payee", "merchant", "merchant name", "narrative",
    "particulars", "reference description",
]
AMOUNT_ALIASES = ["amount", "transaction amount", "amt", "value", "charge amount", "purchase amount"]
DEBIT_ALIASES = ["debit", "debit amount", "withdrawal", "withdrawals", "money out", "outflow", "charges"]
CREDIT_ALIASES = ["credit", "credit amount", "deposit", "deposits", "money in", "inflow", "payments"]


class CSVParseError(ValueError):
    pass


def _normalize_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).strip().lower()).strip()


def _find(columns: dict[str, str], aliases: list[str]) -> str | None:
    for alias in aliases:
        normalized = _normalize_header(alias)
        if normalized in columns:
            return columns[normalized]
    return None


def _infer_date_column(df: pd.DataFrame, excluded: set) -> str | None:
    candidates = []
    for column in df.columns:
        name = _normalize_header(column)
        if column in excluded or not any(token in name for token in ("date", "posted", "posting", "purchase")):
            continue
        values = df[column].dropna().head(20)
        if values.empty:
            continue
        valid_ratio = pd.to_datetime(values, errors="coerce").notna().mean()
        if valid_ratio >= 0.7:
            candidates.append((valid_ratio, column))
    return max(candidates, default=(0, None))[1]


def _infer_description_column(df: pd.DataFrame, excluded: set) -> str | None:
    candidates = []
    ignored_terms = ("balance", "category", "type", "status", "reference", "account", "currency", "number", "id")
    for column in df.columns:
        name = _normalize_header(column)
        if column in excluded or any(term in name for term in ignored_terms):
            continue
        values = df[column].dropna().head(30).astype(str).str.strip()
        if values.empty:
            continue
        text_ratio = values.map(lambda value: _to_float(value) is None and pd.isna(pd.to_datetime(value, errors="coerce"))).mean()
        if text_ratio < 0.7:
            continue
        uniqueness = values.nunique() / len(values)
        average_length = values.str.len().mean()
        candidates.append((uniqueness + min(average_length, 80) / 80, column))
    return max(candidates, default=(0, None))[1]


def _infer_amount_column(df: pd.DataFrame, excluded: set) -> str | None:
    candidates = []
    ignored_terms = ("balance", "available", "limit", "running total")
    for column in df.columns:
        name = _normalize_header(column)
        if column in excluded or any(term in name for term in ignored_terms):
            continue
        values = df[column].dropna().head(30)
        if values.empty:
            continue
        numeric_ratio = values.map(lambda value: _to_float(value) is not None).mean()
        if numeric_ratio < 0.7:
            continue
        semantic_match = any(term in name.split() for term in ("amount", "amt", "value", "charge", "purchase", "debit", "credit"))
        candidates.append((numeric_ratio + (1 if semantic_match else 0), column, semantic_match))

    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda candidate: candidate[0])
    if len(candidates) > 1 and not candidates[0][2] and candidates[0][0] == candidates[1][0]:
        return None
    return candidates[0][1] if candidates[0][2] or len(candidates) == 1 else None


def _to_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = s.replace("(", "").replace(")", "").replace("$", "").replace(",", "").strip()
    if not s:
        return None
    try:
        num = float(s)
    except ValueError:
        return None
    return -num if negative else num


def parse_csv(content: bytes) -> list[dict]:
    """Parse raw CSV bytes into normalized transaction dicts.

    Raises CSVParseError with a helpful message when required columns are
    missing so the API can return a 400 rather than a 500.
    """
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:  # noqa: BLE001 - surface a clean 400
        raise CSVParseError(f"Could not read CSV: {exc}") from exc

    if df.empty:
        raise CSVParseError("The CSV file has no rows.")

    # Map lowercased/stripped column name -> original column name.
    colmap = {_normalize_header(c): c for c in df.columns}

    date_col = _find(colmap, DATE_ALIASES)
    if date_col is None:
        date_col = _infer_date_column(df, set())
    desc_col = _find(colmap, DESC_ALIASES)
    if desc_col is None:
        desc_col = _infer_description_column(df, {date_col} if date_col else set())
    amount_col = _find(colmap, AMOUNT_ALIASES)
    debit_col = _find(colmap, DEBIT_ALIASES)
    credit_col = _find(colmap, CREDIT_ALIASES)
    excluded = {column for column in (date_col, desc_col) if column is not None}
    if amount_col is None and debit_col is None and credit_col is None:
        amount_col = _infer_amount_column(df, excluded)

    if date_col is None or desc_col is None:
        raise CSVParseError(
            "CSV must include a date column and a description column. "
            f"Found columns: {', '.join(str(c) for c in df.columns)}"
        )
    if amount_col is None and debit_col is None and credit_col is None:
        raise CSVParseError(
            "CSV must include an 'amount' column, or 'debit'/'credit' columns."
        )

    rows: list[dict] = []
    for _, row in df.iterrows():
        raw_date = row.get(date_col)
        parsed_date = pd.to_datetime(raw_date, errors="coerce")
        if pd.isna(parsed_date):
            continue
        description = str(row.get(desc_col, "")).strip()
        if not description or description.lower() == "nan":
            description = "(no description)"

        if amount_col is not None:
            amount = _to_float(row.get(amount_col))
        else:
            debit = _to_float(row.get(debit_col)) if debit_col else None
            credit = _to_float(row.get(credit_col)) if credit_col else None
            amount = 0.0
            if credit:
                amount += abs(credit)
            if debit:
                amount -= abs(debit)
        if amount is None:
            continue

        rows.append(
            {
                "date": parsed_date.date() if hasattr(parsed_date, "date") else date.today(),
                "description": description[:255],
                "amount": round(float(amount), 2),
            }
        )

    if not rows:
        raise CSVParseError("No valid transaction rows could be parsed from the CSV.")
    return rows
