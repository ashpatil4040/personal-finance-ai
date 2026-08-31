"""Phase 4: Personal RAG over the user's transactions (pgvector + OpenAI).

Embeddings are generated with OpenAI and stored in the ``transactions.embedding``
pgvector column. Everything is optional: when the LLM/key is unavailable, these
functions are safe no-ops so the rest of the app is unaffected.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from . import llm
from .config import get_settings
from .models import Transaction


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Embed a batch of texts with OpenAI. Returns None on any failure/no-key."""
    if not llm.llm_available() or not texts:
        return None
    from openai import OpenAI

    settings = get_settings()
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.embeddings.create(model=settings.embedding_model, input=texts)
        return [d.embedding for d in resp.data]
    except Exception:  # noqa: BLE001 - embeddings are best-effort
        return None


def backfill_embeddings(db: Session, user_id: int, limit: int = 500) -> int:
    """Embed the user's transactions that don't yet have an embedding.

    Self-healing: lets embeddings be created lazily once a key becomes available,
    even for rows inserted while the LLM was off. Returns the number embedded.
    """
    rows = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.embedding.is_(None))
        .limit(limit)
        .all()
    )
    if not rows:
        return 0
    vectors = embed_texts([r.description for r in rows])
    if not vectors or len(vectors) != len(rows):
        return 0
    for row, vec in zip(rows, vectors):
        row.embedding = vec
    db.commit()
    return len(rows)


def search_similar(db: Session, user_id: int, query: str, k: int = 5) -> list[Transaction]:
    """Semantic search over the user's transactions by cosine similarity."""
    query_vec = embed_texts([query])
    if not query_vec:
        return []
    backfill_embeddings(db, user_id)
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.embedding.isnot(None))
        .order_by(Transaction.embedding.cosine_distance(query_vec[0]))
        .limit(min(k, 25))
        .all()
    )
