"""Lightweight, dependency-free "AI" layer.

Categorization uses keyword matching and insights are generated from simple
heuristics over the user's transactions. This keeps the app fully functional
end-to-end without any external API keys. The functions are structured so a
real LLM backend can be swapped in later behind the same interface.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Groceries": ["grocery", "supermarket", "whole foods", "trader joe", "aldi", "safeway", "market"],
    "Dining": ["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "pizza", "bar", "diner", "grubhub", "doordash", "uber eats"],
    "Transport": ["uber", "lyft", "gas", "shell", "chevron", "fuel", "metro", "transit", "parking", "toll"],
    "Housing": ["rent", "mortgage", "landlord", "hoa"],
    "Utilities": ["electric", "water", "gas bill", "internet", "comcast", "verizon", "at&t", "utility", "phone"],
    "Entertainment": ["netflix", "spotify", "hulu", "disney", "cinema", "movie", "game", "steam", "concert"],
    "Shopping": ["amazon", "target", "walmart", "store", "mall", "clothing", "nike", "best buy"],
    "Health": ["pharmacy", "cvs", "walgreens", "doctor", "dental", "gym", "fitness", "clinic", "hospital"],
    "Income": ["salary", "payroll", "paycheck", "deposit", "refund", "interest", "dividend"],
}


def categorize(description: str, amount: float | None = None) -> str:
    """Return a best-guess category for a transaction description."""
    text = (description or "").lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    if amount is not None and amount > 0:
        return "Income"
    return "Uncategorized"


def _month_key(d) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def generate_insights(transactions: Iterable) -> dict:
    """Produce a spending summary plus natural-language insights."""
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
    monthly_spending = [
        {"month": m, "amount": round(a, 2)} for m, a in sorted(monthly.items())
    ]

    insights: list[str] = []
    if not txns:
        insights.append("No transactions yet. Add some to unlock personalized insights.")
    else:
        if total_income > 0:
            if savings_rate >= 20:
                insights.append(
                    f"Great job! You're saving {savings_rate:.0f}% of your income, above the recommended 20%."
                )
            elif savings_rate >= 0:
                insights.append(
                    f"You're saving {savings_rate:.0f}% of your income. Aim for 20% to build a healthy buffer."
                )
            else:
                insights.append(
                    f"You spent {abs(savings_rate):.0f}% more than you earned this period. Consider trimming expenses."
                )

        if by_category:
            top = by_category[0]
            share = (top["amount"] / total_spending * 100) if total_spending else 0
            insights.append(
                f"Your biggest spending category is {top['category']} at ${top['amount']:.2f} ({share:.0f}% of spending)."
            )

        dining = spending_by_category.get("Dining", 0.0)
        if dining and total_spending and dining / total_spending > 0.15:
            insights.append(
                f"Dining out cost ${dining:.2f}. Cooking a few more meals at home could free up cash for savings."
            )

        if len(monthly_spending) >= 2:
            last, prev = monthly_spending[-1], monthly_spending[-2]
            # Skip the comparison when the most recent month is still sparse
            # (a partial month) to avoid misleading swings from a few records.
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
