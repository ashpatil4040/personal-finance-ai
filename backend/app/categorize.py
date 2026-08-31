"""Transaction categorization.

Rule-based keyword matching is the deterministic baseline (Phase 1). When the
LLM is enabled (Phase 2+), ``categorize``/``categorize_batch`` use OpenAI for
better accuracy and fall back to the rules on any failure or low-confidence
result. The category taxonomy is fixed so downstream charts stay stable.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Groceries": ["grocery", "supermarket", "whole foods", "trader joe", "aldi", "safeway", "market", "kroger", "costco"],
    "Dining": ["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "pizza", "bar ", "diner", "grubhub", "doordash", "uber eats", "chipotle"],
    "Transport": ["uber", "lyft", "gas", "shell", "chevron", "fuel", "metro", "transit", "parking", "toll", "exxon"],
    "Housing": ["rent", "mortgage", "landlord", "hoa"],
    "Utilities": ["electric", "water bill", "internet", "comcast", "verizon", "at&t", "utility", "phone", "t-mobile"],
    "Entertainment": ["netflix", "spotify", "hulu", "disney", "cinema", "movie", "game", "steam", "concert", "hbo"],
    "Shopping": ["amazon", "target", "walmart", "store", "mall", "clothing", "nike", "best buy", "ebay"],
    "Health": ["pharmacy", "cvs", "walgreens", "doctor", "dental", "gym", "fitness", "clinic", "hospital"],
    "Income": ["salary", "payroll", "paycheck", "direct deposit", "deposit", "refund", "interest", "dividend"],
}

# Fixed taxonomy the LLM must choose from (keys + Uncategorized).
CATEGORIES: list[str] = list(CATEGORY_KEYWORDS.keys()) + ["Uncategorized"]


def rule_categorize(description: str, amount: float | None = None) -> str:
    """Deterministic keyword-based categorization (always available)."""
    text = (description or "").lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    if amount is not None and amount > 0:
        return "Income"
    return "Uncategorized"


def categorize(description: str, amount: float | None = None) -> str:
    """Categorize one transaction, using the LLM when available."""
    return categorize_batch([{"description": description, "amount": amount}])[0]


def categorize_batch(items: list[dict]) -> list[str]:
    """Categorize many transactions in one shot.

    Uses a single LLM call when enabled; any item the LLM can't confidently
    place (invalid label or failure) falls back to the deterministic rules.
    """
    rule = [rule_categorize(i.get("description", ""), i.get("amount")) for i in items]
    if not items:
        return rule

    from . import llm  # lazy to avoid import cost when LLM is off

    if not llm.llm_available():
        return rule

    predicted = llm.llm_categorize(items, CATEGORIES)
    if not predicted or len(predicted) != len(items):
        return rule
    return [
        p if p in CATEGORIES and p != "Uncategorized" else rule[idx]
        for idx, p in enumerate(predicted)
    ]


def _month_key(d) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def generate_insights(transactions: Iterable) -> dict:
    """Deterministic spending summary plus plain-language insights."""
    txns = list(transactions)

    total_income = sum(t.amount for t in txns if t.amount > 0)
    total_spending = sum(-t.amount for t in txns if t.amount < 0)
    net = total_income - total_spending
    savings_rate = (net / total_income * 100) if total_income > 0 else 0.0

    spending_by_category: dict[str, float] = defaultdict(float)
    for t in txns:
        if t.amount < 0:
            spending_by_category[t.category] += -t.amount
    by_category = [
        {"category": c, "amount": round(a, 2)}
        for c, a in sorted(spending_by_category.items(), key=lambda kv: kv[1], reverse=True)
    ]

    monthly: dict[str, float] = defaultdict(float)
    monthly_counts: dict[str, int] = defaultdict(int)
    for t in txns:
        if t.amount < 0:
            key = _month_key(t.date)
            monthly[key] += -t.amount
            monthly_counts[key] += 1
    monthly_spending = [{"month": m, "amount": round(a, 2)} for m, a in sorted(monthly.items())]

    insights: list[str] = []
    if not txns:
        insights.append("No transactions yet. Upload a statement to unlock insights.")
    else:
        if total_income > 0:
            if savings_rate >= 20:
                insights.append(f"Great job! You're saving {savings_rate:.0f}% of your income, above the recommended 20%.")
            elif savings_rate >= 0:
                insights.append(f"You're saving {savings_rate:.0f}% of your income. Aim for 20% to build a healthy buffer.")
            else:
                insights.append(f"You spent {abs(savings_rate):.0f}% more than you earned this period. Consider trimming expenses.")
        if by_category:
            top = by_category[0]
            share = (top["amount"] / total_spending * 100) if total_spending else 0
            insights.append(f"Your biggest spending category is {top['category']} at ${top['amount']:.2f} ({share:.0f}% of spending).")
        dining = spending_by_category.get("Dining", 0.0)
        if dining and total_spending and dining / total_spending > 0.15:
            insights.append(f"Dining out cost ${dining:.2f}. Cooking a few more meals at home could free up cash for savings.")
        if len(monthly_spending) >= 2:
            last, prev = monthly_spending[-1], monthly_spending[-2]
            last_is_partial = monthly_counts.get(last["month"], 0) < 3
            if prev["amount"] > 0 and not last_is_partial:
                change = (last["amount"] - prev["amount"]) / prev["amount"] * 100
                trend = "up" if change > 0 else "down"
                insights.append(
                    f"Spending is {trend} {abs(change):.0f}% versus the previous month (${last['amount']:.2f} vs ${prev['amount']:.2f})."
                )

    return {
        "summary": {
            "total_income": round(total_income, 2),
            "total_spending": round(total_spending, 2),
            "net": round(net, 2),
            "savings_rate": round(savings_rate, 1),
            "transaction_count": len(txns),
        },
        "spending_by_category": by_category,
        "monthly_spending": monthly_spending,
        "insights": insights,
    }
