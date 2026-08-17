"""CSV statement parsing and normalization (Phase 1).

Accepts common bank/credit-card CSV exports with flexible column names and
normalizes them to (date, description, amount) rows. Amount convention:
positive = income, negative = spending. Supports either a single signed
``amount`` column or separate debit/credit columns.
"""

from __future__ import annotations

import io
from datetime import date

import pandas as pd

DATE_ALIASES = ["date", "transaction date", "posted date", "post date", "trans date"]
DESC_ALIASES = ["description", "desc", "details", "memo", "name", "payee", "merchant"]
AMOUNT_ALIASES = ["amount", "amt", "value"]
DEBIT_ALIASES = ["debit", "withdrawal", "withdrawals", "money out", "outflow"]
CREDIT_ALIASES = ["credit", "deposit", "deposits", "money in", "inflow"]


class CSVParseError(ValueError):
    pass


def _find(columns: dict[str, str], aliases: list[str]) -> str | None:
    for alias in aliases:
        if alias in columns:
            return columns[alias]
    return None


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
    colmap = {str(c).strip().lower(): c for c in df.columns}

    date_col = _find(colmap, DATE_ALIASES)
    desc_col = _find(colmap, DESC_ALIASES)
    amount_col = _find(colmap, AMOUNT_ALIASES)
    debit_col = _find(colmap, DEBIT_ALIASES)
    credit_col = _find(colmap, CREDIT_ALIASES)

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
