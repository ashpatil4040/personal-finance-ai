"""LLM-assisted extraction (Phase 2).

Falls back to OpenAI to extract structured transactions from raw statement text
when the deterministic parsers can't. This is intentionally optional: it
activates only when ``PFAI_LLM_ENABLED=true`` and an OpenAI API key is available
(``OPENAI_API_KEY`` or ``PFAI_OPENAI_API_KEY``), so the app runs fully without
any key.

The response-parsing logic (``parse_llm_json``) is a pure function so it can be
unit-tested without calling the API.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from .config import get_settings

_PROMPT = """You are a financial statement parser. Extract every transaction from the \
statement text below. Return ONLY a JSON array (no prose, no code fences) where each \
element is an object with exactly these keys:
- "date": ISO format YYYY-MM-DD
- "description": the merchant/description string
- "amount": a number; NEGATIVE for money spent/debited, POSITIVE for money received/credited

Statement text:
---
{text}
---
JSON:"""


def llm_available() -> bool:
    """True when the LLM fallback is enabled, keyed, and the SDK is importable."""
    settings = get_settings()
    if not settings.llm_enabled or not settings.openai_api_key:
        return False
    try:
        import openai  # noqa: F401
    except ImportError:
        return False
    return True


def _coerce_amount(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.replace("$", "").replace(",", "").strip()
        neg = s.startswith("(") and s.endswith(")")
        s = s.strip("()")
        try:
            num = float(s)
        except ValueError:
            return None
        return -num if neg else num
    return None


def parse_llm_json(content: str) -> list[dict]:
    """Parse a model response into normalized transaction rows.

    Tolerates code fences and surrounding prose by extracting the first JSON
    array found. Rows with an unparseable date or amount are skipped.
    """
    text = content.strip()
    # Strip ```json ... ``` fences if present.
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # Fall back to the first [...] block.
    if not text.startswith("["):
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            text = m.group(0)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []

    rows: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        raw_date = str(item.get("date", "")).strip()
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                parsed_date = datetime.strptime(raw_date, fmt).date()
                break
            except ValueError:
                continue
        if parsed_date is None:
            continue
        amount = _coerce_amount(item.get("amount"))
        if amount is None:
            continue
        description = str(item.get("description", "")).strip() or "(no description)"
        rows.append({"date": parsed_date, "description": description[:255], "amount": round(amount, 2)})
    return rows


_CATEGORIZE_PROMPT = """You are a personal-finance transaction categorizer. Assign each \
transaction to exactly one category from this fixed list:
{categories}

Rules:
- Positive amounts are usually "Income".
- Choose the single best category; use "Uncategorized" only if truly unclear.
- Return ONLY a JSON array of category strings, one per transaction, in the same order.

Transactions:
{lines}
JSON:"""


def parse_category_list(content: str, n: int, allowed: list[str]) -> list[str] | None:
    """Parse a model response into exactly ``n`` category labels.

    Returns None if the response can't be parsed into a list of length n.
    Unknown labels are coerced to "Uncategorized" (the caller then falls back
    to the rule-based label for those).
    """
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("["):
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            text = m.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list) or len(data) != n:
        return None
    allowed_set = set(allowed)
    return [c if isinstance(c, str) and c in allowed_set else "Uncategorized" for c in data]


def llm_categorize(items: list[dict], allowed: list[str]) -> list[str] | None:
    """Categorize transactions in a single OpenAI call. Returns None on failure."""
    if not llm_available() or not items:
        return None
    from openai import OpenAI

    settings = get_settings()
    lines = "\n".join(
        f"{i + 1}. {str(it.get('description', '')).strip()} (amount {it.get('amount')})"
        for i, it in enumerate(items)
    )
    prompt = _CATEGORIZE_PROMPT.format(categories=", ".join(allowed), lines=lines)
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        content = resp.choices[0].message.content or ""
        return parse_category_list(content, len(items), allowed)
    except Exception:  # noqa: BLE001 - never crash the request
        return None


def extract_transactions_from_text(text: str) -> list[dict]:
    """Call OpenAI to extract transactions. Returns [] on any failure."""
    if not llm_available() or not text.strip():
        return []
    from openai import OpenAI

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    try:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            messages=[{"role": "user", "content": _PROMPT.format(text=text[:12000])}],
        )
        content = resp.choices[0].message.content or ""
        return parse_llm_json(content)
    except Exception:  # noqa: BLE001 - fallback must never crash the request
        return []
