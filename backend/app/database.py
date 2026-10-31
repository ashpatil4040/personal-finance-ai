from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()

def _normalize_url(url: str) -> str:
    # Hosted providers (Neon, Render) hand out postgres:// or postgresql:// URLs.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


engine = create_engine(_normalize_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def ensure_pgvector() -> None:
    """Idempotently ensure the vector extension and the embedding column exist.

    Runs before create_all so a fresh DB can create the vector column, and adds
    the column to an already-existing transactions table (create_all never
    alters existing tables). Safe to call on every startup.
    """
    if engine.url.get_backend_name() != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(
            text("ALTER TABLE IF EXISTS transactions ADD COLUMN IF NOT EXISTS embedding vector(1536)")
        )
        conn.execute(
            text(
                "ALTER TABLE IF EXISTS knowledge_chunks "
                "ADD COLUMN IF NOT EXISTS embedding vector(1536)"
            )
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
