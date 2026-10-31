"""Phase 5: LangGraph multi-agent orchestration.

A router sends each question to a specialist ReAct agent:

- **analytics** — spending, transactions, savings scenarios, Personal RAG
- **anomaly** — unusual / duplicate / outlier charges
- **research** — Knowledge RAG + web search (evergreen advice and current info)
- **general** — all tools, for advice that needs both the user's data and research

Tools are built per request and closed over the caller's DB session + user id,
so every query is strictly scoped. Specialists are instructed to answer only
from tool output, never inventing numbers.
"""

from __future__ import annotations

from collections import defaultdict
import re
from datetime import date, datetime
from typing import Literal, TypedDict

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import anomalies, knowledge, rag, websearch
from .categorize import generate_insights
from .config import get_settings
from .models import Transaction

Route = Literal["analytics", "anomaly", "research", "general"]

ANALYTICS_PROMPT = (
    "You are the analytics specialist for a personal-finance assistant. Answer "
    "using ONLY the provided tools, which return this specific user's real "
    "transaction data. Always ground answers in concrete numbers from the tools "
    "and never invent figures. Format currency like $1,234.56. If the question "
    "is not about the user's finances, say you can only help with their money "
    "data. Keep answers concise (2-4 sentences)."
)

ANOMALY_PROMPT = (
    "You are the anomaly/fraud specialist. Use detect_anomalies first. Ground "
    "every claim in tool output — never invent a suspicious charge. Explain "
    "why each item was flagged (duplicate, outlier, new merchant) and stay "
    "calm: these are heuristics, not proof of fraud. If nothing was flagged, "
    "say so clearly. Keep answers concise."
)

RESEARCH_PROMPT = (
    "You are the research specialist. Use search_finance_knowledge for evergreen "
    "personal-finance guidance (budgeting rules, emergency funds, debt payoff). "
    "Use search_web for current/external facts (interest rates, inflation, news). "
    "Cite sources by title. This is educational, not personalized financial "
    "advice. Never invent rates or statistics. Keep answers concise (3-6 sentences)."
)

GENERAL_PROMPT = (
    "You are a personal-finance advisor. Combine the user's real transactions "
    "(analytics/anomaly tools) with knowledge-base and web research when the "
    "question needs both. Ground every number in tool output. Never invent "
    "figures. Educational only — not personalized financial advice. "
    "Format currency like $1,234.56. Keep answers concise."
)

ANOMALY_KEYWORDS = (
    "unusual",
    "anomal",
    "fraud",
    "suspicious",
    "duplicate",
    "charged twice",
    "double charge",
    "double-charged",
    "weird charge",
    "strange charge",
    "odd transaction",
    "unauthorized",
    "outlier",
    "scam",
    "stolen",
    "did i get charged",
    "anything weird",
    "anything unusual",
    "red flag",
)

RESEARCH_KEYWORDS = (
    "inflation",
    "interest rate",
    "federal funds",
    "fed funds",
    "50/30/20",
    "50-30-20",
    "50 30 20",
    "emergency fund",
    "high-yield",
    "hysa",
    "apy",
    "apr",
    "debt avalanche",
    "debt snowball",
    "credit utilization",
    "sinking fund",
    "rule of thumb",
    "budget rule",
    "search the web",
    "look up",
    "on the web",
    "current rate",
    "healthy savings",
)

GENERAL_KEYWORDS = (
    "advice",
    "recommend",
    "what should i do",
    "how can i improve",
    "tips for",
    "help me budget",
    "help me plan",
    "how should i",
)


def classify_question(question: str) -> Route:
    """Keyword router. Deterministic so tests (and no-LLM paths) stay stable."""
    q = (question or "").lower()

    def hit(keywords: tuple[str, ...]) -> bool:
        # Word-start match; short keywords ("apr") must also end a word so they don't fire on "April".
        return any(
            re.search(r"(?<![a-z0-9])" + re.escape(k) + (r"(?![a-z0-9])" if len(k) <= 4 else ""), q)
            for k in keywords
        )

    if hit(ANOMALY_KEYWORDS):
        return "anomaly"
    if hit(RESEARCH_KEYWORDS):
        return "research"
    if hit(GENERAL_KEYWORDS):
        return "general"
    return "analytics"


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

    def _filtered(category, start_date, end_date, min_amount, max_amount, description_contains):
        q = _user_txns()
        if category:
            q = q.filter(func.lower(Transaction.category) == category.strip().lower())
        sd, ed = _parse_date(start_date), _parse_date(end_date)
        if sd:
            q = q.filter(Transaction.date >= sd)
        if ed:
            q = q.filter(Transaction.date <= ed)
        if min_amount is not None:
            q = q.filter(Transaction.amount >= min_amount)
        if max_amount is not None:
            q = q.filter(Transaction.amount <= max_amount)
        if description_contains:
            q = q.filter(Transaction.description.ilike(f"%{description_contains.strip()}%"))
        return q

    @tool
    def query_transactions(
        category: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        description_contains: str | None = None,
        limit: int = 50,
    ) -> dict:
        """Look up the user's individual transactions. Optionally filter by
        category (case-insensitive), an inclusive date range (YYYY-MM-DD), an
        amount range (negative = spending, positive = income), and/or a merchant
        text match via `description_contains`. Returns `total_matches`, the exact
        `total_amount` over ALL matches, and up to `limit` transactions (most
        recent first). Never sum the listed rows yourself; use `total_amount`."""
        q = _filtered(category, start_date, end_date, min_amount, max_amount, description_contains)
        total_matches, total_amount = q.with_entities(
            func.count(Transaction.id), func.coalesce(func.sum(Transaction.amount), 0.0)
        ).one()
        rows = q.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(min(limit, 200)).all()
        return {
            "total_matches": int(total_matches),
            "total_amount": round(float(total_amount), 2),
            "returned": len(rows),
            "transactions": [
                {
                    "date": t.date.isoformat(),
                    "description": t.description,
                    "amount": t.amount,
                    "category": t.category,
                }
                for t in rows
            ],
        }

    @tool
    def aggregate_transactions(
        category: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        description_contains: str | None = None,
        group_by: Literal["none", "category", "month", "merchant"] = "none",
        include_transfers: bool = False,
    ) -> dict:
        """Compute EXACT totals over the user's transactions for questions like
        "how much did I spend on X in March", "how many times", "average",
        or "top merchants". Filters: category (case-insensitive), date range
        (YYYY-MM-DD), merchant text. `group_by` splits results by category,
        month (YYYY-MM) or merchant. Transfers (Zelle/ATM/card payments) are
        excluded from spending unless include_transfers=true."""
        q = _filtered(category, start_date, end_date, None, None, description_contains)
        txns = q.all()
        if not include_transfers:
            txns = [t for t in txns if t.category != "Transfer"]

        def summarize(items):
            spent = sum(-t.amount for t in items if t.amount < 0)
            income = sum(t.amount for t in items if t.amount > 0)
            return {
                "count": len(items),
                "total_spent": round(spent, 2),
                "total_income": round(income, 2),
                "net": round(income - spent, 2),
            }

        out = {"overall": summarize(txns)}
        if group_by != "none":
            groups: dict[str, list] = defaultdict(list)
            for t in txns:
                if group_by == "category":
                    key = t.category or "Uncategorized"
                elif group_by == "month":
                    key = f"{t.date.year:04d}-{t.date.month:02d}"
                else:
                    key = t.description.strip().lower()[:40]
                groups[key].append(t)
            rows = [{"group": k, **summarize(v)} for k, v in groups.items()]
            rows.sort(key=lambda r: (-r["total_spent"], r["group"]))
            out["groups"] = rows[:25]
        return out

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
        spend = [
            t for t in txns
            if t.amount < 0
            and t.category != "Transfer"
            and (category is None or t.category == category)
        ]
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

    @tool
    def search_similar_transactions(query: str, k: int = 5) -> list[dict]:
        """Semantically search the user's transactions by meaning (Personal RAG),
        not just exact keywords. Use for fuzzy questions like "recurring
        subscriptions", "coffee runs", or "anything like insurance". Returns the
        most similar transactions."""
        rows = rag.search_similar(db, user_id, query, k=k)
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
    def detect_anomalies() -> dict:
        """Scan the user's transactions for unusual activity: possible duplicate
        charges, amount outliers vs the category median, and first-time large
        merchants. Use for fraud/suspicious/weird-charge questions."""
        return anomalies.detect_anomalies(db, user_id)

    @tool
    def search_finance_knowledge(query: str, k: int = 3) -> list[dict]:
        """Search the built-in personal-finance knowledge base (budgeting rules,
        emergency funds, debt payoff, credit utilization, subscriptions). Use
        for evergreen how-to / rule-of-thumb questions."""
        return knowledge.search_knowledge(db, query, k=k)

    @tool
    def search_web(query: str, k: int = 5) -> list[dict]:
        """Search the public web (DuckDuckGo + Wikipedia) for current or external
        facts such as interest rates, inflation, or news. Returns titles, snippets,
        and source URLs. Use when the knowledge base is not enough."""
        return websearch.search_web(query, k=k)

    analytics = [
        get_spending_summary,
        aggregate_transactions,
        query_transactions,
        calculate_savings_scenario,
        search_similar_transactions,
    ]
    anomaly = [detect_anomalies, query_transactions]
    research = [search_finance_knowledge, search_web]
    general = analytics + [detect_anomalies, search_finance_knowledge, search_web]
    return {
        "analytics": analytics,
        "anomaly": anomaly,
        "research": research,
        "general": general,
    }


PROMPTS: dict[Route, str] = {
    "analytics": ANALYTICS_PROMPT,
    "anomaly": ANOMALY_PROMPT,
    "research": RESEARCH_PROMPT,
    "general": GENERAL_PROMPT,
}


class AgentState(TypedDict, total=False):
    question: str
    route: Route
    answer: str
    tools_used: list[str]
    agent: str


def _extract_result(result: dict) -> tuple[str, list[str]]:
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
    return answer or "I couldn't find an answer.", tools_used


def _data_context(db: Session, user_id: int) -> str:
    lo, hi, n = db.query(
        func.min(Transaction.date), func.max(Transaction.date), func.count(Transaction.id)
    ).filter(Transaction.user_id == user_id).one()
    cats = sorted(
        c for (c,) in db.query(Transaction.category)
        .filter(Transaction.user_id == user_id).distinct().all() if c
    )
    span = f"{lo.isoformat()} to {hi.isoformat()}" if lo and hi else "none"
    return (
        f"\n\nContext: today is {date.today().isoformat()}. The user has {n} transactions "
        f"spanning {span}. Categories present: {', '.join(cats) or 'none'}. "
        "Resolve relative dates ('this month', 'last month') against the data range "
        "and state the exact dates used. For any total, count or average, call "
        "aggregate_transactions or use the tool's total fields; never add numbers "
        "yourself. If the tools return no matching data, say so plainly instead of "
        "guessing."
    )


def build_agent(db: Session, user_id: int):
    """Compile the multi-agent graph (router + four specialist ReAct agents)."""
    settings = get_settings()
    model = ChatOpenAI(
        model=settings.openai_model,
        temperature=0,
        api_key=settings.openai_api_key,
    )
    tools = make_tools(db, user_id)
    context = _data_context(db, user_id)

    def router_node(state: AgentState) -> dict:
        return {"route": classify_question(state.get("question", ""))}

    def make_specialist(route: Route):
        def node(state: AgentState) -> dict:
            specialist = create_react_agent(
                model, tools[route], prompt=PROMPTS[route] + context, name=route
            )
            result = specialist.invoke({"messages": [{"role": "user", "content": state["question"]}]})
            answer, tools_used = _extract_result(result)
            return {"answer": answer, "tools_used": tools_used, "agent": route}

        node.__name__ = f"{route}_node"
        return node

    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    for route in ("analytics", "anomaly", "research", "general"):
        graph.add_node(route, make_specialist(route))  # type: ignore[arg-type]
    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        lambda s: s["route"],
        {
            "analytics": "analytics",
            "anomaly": "anomaly",
            "research": "research",
            "general": "general",
        },
    )
    for route in ("analytics", "anomaly", "research", "general"):
        graph.add_edge(route, END)
    return graph.compile()


def answer_question(db: Session, user_id: int, question: str) -> dict:
    """Run the multi-agent graph for one question.

    Returns {answer, tools_used, agent}.
    """
    graph = build_agent(db, user_id)
    result = graph.invoke({"question": question})
    return {
        "answer": result.get("answer") or "I couldn't find an answer.",
        "tools_used": result.get("tools_used") or [],
        "agent": result.get("agent") or classify_question(question),
    }
