from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, ensure_pgvector
from .routers import accounts, ask, auth, digest, insights, transactions, uploads

# Ensure the pgvector extension + embedding column exist (fresh and existing DBs),
# then create any missing tables. A later phase can introduce Alembic migrations.
ensure_pgvector()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-Assisted Personal Finance API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(uploads.router)
app.include_router(insights.router)
app.include_router(ask.router)
app.include_router(digest.router)
