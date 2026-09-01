"""Phase 5: deterministic anomaly / fraud-style detection.

Flags unusual activity from the user's own history — duplicate charges,
amount outliers vs the category median, and first-time large merchants.
Pure functions so the detector works with no LLM and is unit-tested.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from statistics import median

from sqlalchemy.orm import Session

from .models import Transaction

_SKIP_OUTLIER_CATEGORIES = {"Income", "Housing"}
_DUPLICATE_WINDOW_DAYS = 2
_OUTLIER_MIN_ABS = 75.0
_OUTLIER_MULTIPLIER = 3.0
_NEW_MERCHANT_MIN_ABS = 250.0


def _norm_desc(description: str) -> str:
    return re.sub(r"\s+", " ", (description or "").strip().lower())


def detect_from_txns(txns) -> list[dict]:
    """Return anomaly dicts for transaction-like objects.

    Each item needs ``date``, ``description``, ``amount``, ``category``.
    Optional ``id`` is passed through when present.
    """
    if not txns:
        return []

    flags: list[dict] = []
    seen_keys: set[tuple] = set()

    def _add(kind: str, severity: str, reason: str, t) -> None:
        key = (kind, getattr(t, "id", None), _norm_desc(t.description), t.date, round(t.amount, 2))
        if key in seen_keys:
            return
        seen_keys.add(key)
        flags.append(
            {
                "kind": kind,
                "severity": severity,
                "reason": reason,
                "date": t.date.isoformat() if isinstance(t.date, date) else str(t.date),
                "description": t.description,
                "amount": t.amount,
                "category": t.category,
                "transaction_id": getattr(t, "id", None),
            }
        )

    # --- Duplicates: same merchant + amount within a few days (not monthly) ---
    groups: dict[tuple[str, float], list] = defaultdict(list)
    for t in txns:
        if t.amount >= 0:
            continue
        groups[(_norm_desc(t.description), round(t.amount, 2))].append(t)
    for (_desc, _amt), rows in groups.items():
        rows = sorted(rows, key=lambda x: x.date)
        for prev, cur in zip(rows, rows[1:]):
            gap = (cur.date - prev.date).days
            if 0 <= gap <= _DUPLICATE_WINDOW_DAYS:
                _add(
                    "duplicate",
                    "high",
                    f"Possible duplicate: same merchant and amount "
                    f"{gap} day{'s' if gap != 1 else ''} apart "
                    f"({prev.date.isoformat()} and {cur.date.isoformat()}).",
                    cur,
                )

    # --- Amount outliers vs category median ---
    by_cat: dict[str, list] = defaultdict(list)
    for t in txns:
        if t.amount < 0 and t.category not in _SKIP_OUTLIER_CATEGORIES:
            by_cat[t.category].append(t)
    for cat, rows in by_cat.items():
        abs_amts = [-t.amount for t in rows]
        if len(abs_amts) < 3:
            continue
        med = median(abs_amts)
        if med <= 0:
            continue
        threshold = max(_OUTLIER_MIN_ABS, med * _OUTLIER_MULTIPLIER)
        for t in rows:
            spend = -t.amount
            if spend >= threshold and spend > med * 1.5:
                _add(
                    "amount_outlier",
                    "high" if spend >= med * 5 else "medium",
                    f"{t.category} charge ${spend:.2f} is "
                    f"{spend / med:.1f}× the category median (${med:.2f}).",
                    t,
                )

    # --- First-time large merchants in the latest month (needs prior history) ---
    def _month_key(d) -> str:
        return f"{d.year:04d}-{d.month:02d}"

    months = sorted({_month_key(t.date) for t in txns})
    if len(months) >= 2:
        latest = months[-1]
        prior = {_norm_desc(t.description) for t in txns if _month_key(t.date) != latest}
        for t in txns:
            if _month_key(t.date) != latest or t.amount >= 0:
                continue
            if t.category in _SKIP_OUTLIER_CATEGORIES:
                continue
            if _norm_desc(t.description) in prior:
                continue
            if -t.amount >= _NEW_MERCHANT_MIN_ABS:
                _add(
                    "new_merchant",
                    "high" if -t.amount >= 400 else "medium",
                    f"First time seeing this merchant, and the charge is ${-t.amount:.2f}.",
                    t,
                )

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    flags.sort(key=lambda f: (severity_rank.get(f["severity"], 9), f["date"]), reverse=False)
    return flags


def _summary(flags: list[dict]) -> str:
    if not flags:
        return "No unusual activity detected in your transactions."
    counts: dict[str, int] = defaultdict(int)
    for f in flags:
        counts[f["kind"]] += 1
    labels = {
        "duplicate": "possible duplicate",
        "amount_outlier": "amount outlier",
        "new_merchant": "new merchant",
    }
    parts = []
    for kind, n in counts.items():
        label = labels.get(kind, kind)
        parts.append(f"{n} {label}{'s' if n != 1 else ''}")
    return f"{len(flags)} unusual item{'s' if len(flags) != 1 else ''} flagged: " + ", ".join(parts) + "."


def detect_anomalies(db: Session, user_id: int) -> dict:
    txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )
    flags = detect_from_txns(txns)
    return {
        "count": len(flags),
        "summary": _summary(flags),
        "anomalies": flags,
    }
