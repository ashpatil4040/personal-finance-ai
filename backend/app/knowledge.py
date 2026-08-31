"""Phase 5: Knowledge RAG — a curated personal-finance corpus over pgvector.

Distinct from Personal RAG (user transactions). Chunks are global, seeded
idempotently, and embedded with OpenAI when a key is present. Keyword overlap
is the fallback so research still works with the LLM off.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from . import llm, rag
from .models import KnowledgeChunk

# Evergreen, educational personal-finance notes. Short enough to retrieve whole.
CORPUS: list[tuple[str, str, str, str]] = [
    (
        "50-30-20",
        "The 50/30/20 budget rule",
        "budgeting",
        "The 50/30/20 rule of thumb splits take-home pay into 50% needs "
        "(housing, utilities, groceries, minimum debt payments), 30% wants "
        "(dining out, entertainment, hobbies), and 20% savings and extra debt "
        "paydown. It is a starting point, not a law: high housing costs in "
        "expensive cities often push needs above 50%, in which case trim wants "
        "first and automate whatever savings rate you can sustain.",
    ),
    (
        "emergency-fund",
        "Emergency fund size",
        "savings",
        "A common emergency-fund target is 3–6 months of essential expenses "
        "(rent, food, insurance, minimum debt payments) in a liquid account "
        "such as a high-yield savings account. People with variable income or "
        "a single earner often aim closer to 6–12 months. Fund it before "
        "aggressive investing, and replenish after you use it. Do not invest "
        "this money in stocks — the point is stability, not return.",
    ),
    (
        "savings-rate",
        "Healthy savings rate",
        "savings",
        "A widely cited target is saving at least 15–20% of gross income toward "
        "retirement (including employer match) plus a separate emergency fund. "
        "If you are paying down high-interest debt, count extra principal "
        "payments toward that 20% 'future you' bucket. Track savings rate as "
        "(income − spending) / income over a full month, not a single paycheck.",
    ),
    (
        "debt-avalanche-snowball",
        "Debt avalanche vs snowball",
        "debt",
        "Avalanche: pay minimums on every debt, then put extra money toward the "
        "highest APR first — mathematically cheapest. Snowball: pay the smallest "
        "balance first for quick wins and motivation. Either beats only paying "
        "minimums. Credit-card APRs often exceed 20%; paying those down usually "
        "beats investing extra cash at a lower expected return.",
    ),
    (
        "credit-utilization",
        "Credit utilization",
        "credit",
        "Credit utilization is the share of revolving credit you are using. "
        "Scoring models often treat under 30% as fine and under 10% as excellent. "
        "Utilization is calculated per card and in aggregate. Paying a card down "
        "before the statement closes (not just the due date) is what bureaus see. "
        "Closing old cards can hurt utilization by shrinking your limit.",
    ),
    (
        "subscription-audit",
        "Subscription audit",
        "spending",
        "List every recurring charge (streaming, gym, software, delivery clubs) "
        "and cancel anything you have not used in 30 days. Annual plans hide "
        "in yearly statements — search for 'subscription', 'membership', and "
        "'premium'. A $15/month unused sub is $180/year. After cancelling, "
        "watch the next two statements for 'save your account' retry charges.",
    ),
    (
        "sinking-funds",
        "Sinking funds",
        "budgeting",
        "A sinking fund is money set aside monthly for a known irregular expense "
        "(car insurance, holidays, travel, new tires) so it does not ambush the "
        "month it hits. Divide the annual cost by 12 and automate a transfer to "
        "a separate savings bucket. This keeps your emergency fund for true "
        "emergencies rather than predictable bills.",
    ),
    (
        "high-yield-savings",
        "High-yield savings accounts",
        "savings",
        "High-yield savings accounts (HYSAs) at online banks typically pay a "
        "variable APY far above traditional brick-and-mortar savings. They are "
        "appropriate for emergency funds and near-term goals because principal "
        "is stable (FDIC-insured up to limits) and liquid. APYs move with the "
        "federal-funds rate — look up the current rate rather than relying on "
        "an old article. Do not chase a 0.1% difference if the bank is awkward "
        "to use; convenience is what keeps the emergency fund funded.",
    ),
    (
        "inflation",
        "Inflation and purchasing power",
        "macro",
        "Inflation is the rise in the general price level, which erodes the "
        "purchasing power of cash. The CPI is the common US measure. Cash in a "
        "0% checking account loses real value when inflation is positive; that "
        "is a reason to keep idle cash in an HYSA and to invest long-term money. "
        "For budgeting, if grocery spend is up, check whether prices rose or you "
        "bought more — both can look like a 'spending problem' in a dashboard.",
    ),
]


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 1}


def ensure_corpus(db: Session) -> int:
    """Insert any missing corpus rows. Returns the number newly inserted."""
    existing = {row.slug for row in db.query(KnowledgeChunk.slug).all()}
    added = 0
    for slug, title, topic, content in CORPUS:
        if slug in existing:
            continue
        db.add(KnowledgeChunk(slug=slug, title=title, topic=topic, content=content))
        added += 1
    if added:
        db.commit()
    return added


def keyword_search(query: str, chunks: list[KnowledgeChunk], k: int = 3) -> list[KnowledgeChunk]:
    q = _tokenize(query)
    if not q or not chunks:
        return []
    scored: list[tuple[int, KnowledgeChunk]] = []
    for chunk in chunks:
        blob = _tokenize(f"{chunk.title} {chunk.topic} {chunk.content}")
        overlap = len(q & blob)
        # Title/topic hits count extra so "emergency fund" ranks the right note.
        overlap += 2 * len(q & _tokenize(f"{chunk.title} {chunk.topic}"))
        if overlap:
            scored.append((overlap, chunk))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:k]]


def _backfill_embeddings(db: Session) -> int:
    if not llm.llm_available():
        return 0
    rows = db.query(KnowledgeChunk).filter(KnowledgeChunk.embedding.is_(None)).all()
    if not rows:
        return 0
    texts = [f"{r.title}\n{r.content}" for r in rows]
    vectors = rag.embed_texts(texts)
    if not vectors or len(vectors) != len(rows):
        return 0
    for row, vec in zip(rows, vectors):
        row.embedding = vec
    db.commit()
    return len(rows)


def _to_out(chunk: KnowledgeChunk, extra: dict | None = None) -> dict:
    out = {
        "title": chunk.title,
        "topic": chunk.topic,
        "content": chunk.content,
        "source": "knowledge_base",
    }
    if extra:
        out.update(extra)
    return out


def search_knowledge(db: Session, query: str, k: int = 3) -> list[dict]:
    """Semantic search when embeddings exist; keyword overlap otherwise."""
    ensure_corpus(db)
    _backfill_embeddings(db)

    query_vec = rag.embed_texts([query]) if llm.llm_available() else None
    if query_vec:
        rows = (
            db.query(KnowledgeChunk)
            .filter(KnowledgeChunk.embedding.isnot(None))
            .order_by(KnowledgeChunk.embedding.cosine_distance(query_vec[0]))
            .limit(min(k, 8))
            .all()
        )
        if rows:
            return [_to_out(r) for r in rows]

    chunks = db.query(KnowledgeChunk).all()
    return [_to_out(c) for c in keyword_search(query, chunks, k=k)]
