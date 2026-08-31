"""Phase 4: proactive monthly digest.

Deterministically compares the latest month to the previous one (spending
change, category movers, new categories, largest charges, savings rate). When
the LLM is available it adds a short natural-language narrative + recommendations
grounded strictly in those computed numbers; otherwise it returns a deterministic
narrative so the feature always works.
"""

from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy.orm import Session

from . import llm
from .models import Transaction


def _month_key(d) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def compute_facts(db: Session, user_id: int) -> dict:
    txns = db.query(Transaction).filter(Transaction.user_id == user_id).all()
    return compute_facts_from_txns(txns)


def compute_facts_from_txns(txns) -> dict:
    """Pure month-over-month analysis over transaction-like objects
    (each has ``date``, ``amount``, ``category``). No DB access."""
    by_month_spend: dict[str, float] = defaultdict(float)
    by_month_income: dict[str, float] = defaultdict(float)
    by_month_cat: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    by_month_txns: dict[str, list[Transaction]] = defaultdict(list)
    for t in txns:
        mk = _month_key(t.date)
        by_month_txns[mk].append(t)
        if t.amount < 0:
            by_month_spend[mk] += -t.amount
            by_month_cat[mk][t.category] += -t.amount
        else:
            by_month_income[mk] += t.amount

    months = sorted(by_month_txns.keys())
    if not months:
        return {"has_data": False}

    latest = months[-1]
    prev = months[-2] if len(months) >= 2 else None

    latest_spend = round(by_month_spend[latest], 2)
    prev_spend = round(by_month_spend[prev], 2) if prev else None
    spend_change_pct = (
        round((latest_spend - prev_spend) / prev_spend * 100, 1)
        if prev and prev_spend
        else None
    )

    latest_income = round(by_month_income[latest], 2)
    savings_rate = (
        round((latest_income - latest_spend) / latest_income * 100, 1) if latest_income > 0 else None
    )

    movers = []
    if prev:
        cats = set(by_month_cat[latest]) | set(by_month_cat[prev])
        for c in cats:
            delta = by_month_cat[latest].get(c, 0.0) - by_month_cat[prev].get(c, 0.0)
            if abs(delta) >= 1:
                movers.append({"category": c, "delta": round(delta, 2)})
        movers.sort(key=lambda m: abs(m["delta"]), reverse=True)
    movers = movers[:4]

    new_categories = (
        [c for c in by_month_cat[latest] if c not in by_month_cat[prev]] if prev else []
    )

    largest = sorted(
        [t for t in by_month_txns[latest] if t.amount < 0], key=lambda t: t.amount
    )[:3]
    largest_out = [
        {"description": t.description, "amount": t.amount, "category": t.category} for t in largest
    ]

    top_category = None
    if by_month_cat[latest]:
        tc = max(by_month_cat[latest].items(), key=lambda kv: kv[1])
        top_category = {"category": tc[0], "amount": round(tc[1], 2)}

    return {
        "has_data": True,
        "month": latest,
        "previous_month": prev,
        "total_spending": latest_spend,
        "previous_spending": prev_spend,
        "spend_change_pct": spend_change_pct,
        "income": latest_income,
        "savings_rate": savings_rate,
        "top_category": top_category,
        "category_movers": movers,
        "new_categories": new_categories,
        "largest_transactions": largest_out,
    }


def _deterministic_narrative(f: dict) -> tuple[str, list[str]]:
    parts: list[str] = []
    if f.get("spend_change_pct") is not None:
        direction = "up" if f["spend_change_pct"] > 0 else "down"
        parts.append(
            f"You spent ${f['total_spending']:.2f} in {f['month']}, {direction} "
            f"{abs(f['spend_change_pct']):.0f}% from {f['previous_month']}."
        )
    else:
        parts.append(f"You spent ${f['total_spending']:.2f} in {f['month']}.")
    if f.get("top_category"):
        parts.append(
            f"Your top category was {f['top_category']['category']} at "
            f"${f['top_category']['amount']:.2f}."
        )
    recs: list[str] = []
    for m in f.get("category_movers", []):
        if m["delta"] > 0:
            recs.append(
                f"{m['category']} rose ${m['delta']:.2f} vs last month — a place to trim."
            )
            break
    if f.get("savings_rate") is not None and f["savings_rate"] < 20:
        recs.append(f"Savings rate was {f['savings_rate']:.0f}%; aim for 20%.")
    if not recs:
        recs.append("Spending looks steady — keep it up.")
    return " ".join(parts), recs


def build_digest(db: Session, user_id: int) -> dict:
    facts = compute_facts(db, user_id)
    if not facts.get("has_data"):
        return {
            "has_data": False,
            "narrative": "No transactions yet. Upload a statement to see your monthly digest.",
            "recommendations": [],
            "facts": facts,
        }

    narrative, recommendations = _deterministic_narrative(facts)

    if llm.llm_available():
        enriched = _llm_narrative(facts)
        if enriched:
            narrative, recommendations = enriched

    return {
        "has_data": True,
        "narrative": narrative,
        "recommendations": recommendations,
        "facts": facts,
    }


_DIGEST_PROMPT = """You are a personal-finance assistant writing a monthly digest. \
Use ONLY the numbers in this JSON (do not invent any). Write a friendly 2-3 sentence \
summary and 3 short, specific recommendations grounded in these numbers. Return ONLY \
JSON: {{"narrative": "...", "recommendations": ["...", "...", "..."]}}.

DATA:
{facts}
JSON:"""


def _llm_narrative(facts: dict) -> tuple[str, list[str]] | None:
    from openai import OpenAI

    from .config import get_settings

    settings = get_settings()
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.3,
            messages=[{"role": "user", "content": _DIGEST_PROMPT.format(facts=json.dumps(facts))}],
        )
        content = (resp.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = content.strip("`")
            content = content[content.find("{") :]
        data = json.loads(content[content.find("{") : content.rfind("}") + 1])
        narrative = str(data.get("narrative", "")).strip()
        recs = [str(r).strip() for r in data.get("recommendations", []) if str(r).strip()]
        if narrative and recs:
            return narrative, recs[:3]
    except Exception:  # noqa: BLE001 - fall back to deterministic
        return None
    return None
