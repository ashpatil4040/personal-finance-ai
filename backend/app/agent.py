"""Phase 3: LangGraph analytics agent.

A ReAct agent (OpenAI via langchain-openai) answers natural-language questions
grounded in the user's real transaction data. Tools are built per request and
closed over the caller's DB session + user id, so every query is strictly scoped
to that user. The agent is instructed to answer only from tool output, never
inventing numbers.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from sqlalchemy.orm import Session

from .categorize import generate_insights
from .config import get_settings
from .models import Transaction

SYSTEM_PROMPT = (
    "You are a helpful personal-finance assistant. Answer the user's question "
    "using ONLY the provided tools, which return this specific user's real "
    "transaction data. Always ground answers in concrete numbers from the tools "
    "and never invent figures. Format currency like $1,234.56. If the question "
    "is not about the user's finances, say you can only help with their money "
    "data. Keep answers concise (2-4 sentences)."
)


def _parse_date(value: str | None):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def make_tools(db: Session, user_id: int):
    def _user_txns():
        return db.query(Transaction).filter(Transaction.user_id == user_id)

    @tool
    def get_spending_summary() -> dict:
        """Get the user's overall financial summary: total income, total spending,
        net, savings rate, spending broken down by category, and monthly spending.
        Use this for big-picture questions."""
        return generate_insights(_user_txns().all())

    @tool
    def query_transactions(
        category: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Look up the user's individual transactions. Optionally filter by
        category, an inclusive date range (YYYY-MM-DD), and/or an amount range
        (amounts are negative for spending, positive for income). Returns up to
        `limit` matching transactions, most recent first."""
        q = _user_txns()
        if category:
            q = q.filter(Transaction.category == category)
        sd, ed = _parse_date(start_date), _parse_date(end_date)
        if sd:
            q = q.filter(Transaction.date >= sd)
        if ed:
            q = q.filter(Transaction.date <= ed)
        if min_amount is not None:
            q = q.filter(Transaction.amount >= min_amount)
        if max_amount is not None:
            q = q.filter(Transaction.amount <= max_amount)
        rows = q.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(min(limit, 200)).all()
        return [
            {
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "category": t.category,
            }
            for t in rows
        ]

    @tool
    def calculate_savings_scenario(
        category: str | None = None,
        monthly_reduction: float | None = None,
        percent_reduction: float | None = None,
    ) -> dict:
        """Project how much the user could save. Provide either a fixed
        `monthly_reduction` (dollars/month), or a `percent_reduction` (0-100) of
        their average monthly spending in `category` (or all spending if no
        category). Returns the estimated monthly and annual savings with the
        numbers used."""
        txns = _user_txns().all()
        spend = [t for t in txns if t.amount < 0 and (category is None or t.category == category)]
        months: dict[str, float] = defaultdict(float)
        for t in spend:
            months[f"{t.date.year:04d}-{t.date.month:02d}"] += -t.amount
        n_months = max(len(months), 1)
        avg_monthly = sum(months.values()) / n_months

        if monthly_reduction is not None:
            monthly_savings = max(0.0, float(monthly_reduction))
        elif percent_reduction is not None:
            monthly_savings = avg_monthly * max(0.0, min(percent_reduction, 100.0)) / 100.0
        else:
            monthly_savings = 0.0

        return {
            "scope": category or "all spending",
            "average_monthly_spending": round(avg_monthly, 2),
            "assumed_monthly_savings": round(monthly_savings, 2),
            "projected_annual_savings": round(monthly_savings * 12, 2),
            "months_of_data": n_months,
        }

    return [get_spending_summary, query_transactions, calculate_savings_scenario]


def build_agent(db: Session, user_id: int):
    settings = get_settings()
    model = ChatOpenAI(
        model=settings.openai_model,
        temperature=0,
        api_key=settings.openai_api_key,
    )
    return create_react_agent(model, make_tools(db, user_id), prompt=SYSTEM_PROMPT)


def answer_question(db: Session, user_id: int, question: str) -> dict:
    """Run the agent for one question. Returns {answer, tools_used}."""
    agent = build_agent(db, user_id)
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", [])

    tools_used: list[str] = []
    for m in messages:
        for call in getattr(m, "tool_calls", None) or []:
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
            if name and name not in tools_used:
                tools_used.append(name)

    answer = ""
    for m in reversed(messages):
        content = getattr(m, "content", None)
        if getattr(m, "type", None) == "ai" and content:
            answer = content if isinstance(content, str) else str(content)
            break
    return {"answer": answer or "I couldn't find an answer.", "tools_used": tools_used}
