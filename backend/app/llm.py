"""LLM-assisted extraction (Phase 2).

Falls back to AWS Bedrock (Claude) to extract structured transactions from raw
statement text when the deterministic parsers can't. This is intentionally
optional: it activates only when ``PFAI_LLM_ENABLED=true`` and AWS credentials
are available, so the app runs fully without any cloud keys.

The response-parsing logic (``parse_llm_json``) is a pure function so it can be
unit-tested without calling Bedrock.
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
    """True when the LLM fallback is enabled and boto3 is importable."""
    settings = get_settings()
    if not settings.llm_enabled:
        return False
    try:
        import boto3  # noqa: F401
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


def extract_transactions_from_text(text: str) -> list[dict]:
    """Call Bedrock to extract transactions. Returns [] on any failure."""
    if not llm_available() or not text.strip():
        return []
    import boto3

    settings = get_settings()
    client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": _PROMPT.format(text=text[:12000])}],
    }
    try:
        resp = client.invoke_model(modelId=settings.bedrock_model_id, body=json.dumps(body))
        payload = json.loads(resp["body"].read())
        content = "".join(part.get("text", "") for part in payload.get("content", []))
        return parse_llm_json(content)
    except Exception:  # noqa: BLE001 - fallback must never crash the request
        return []
