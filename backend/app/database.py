from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def ensure_pgvector() -> None:
    """Idempotently ensure the vector extension and the embedding column exist.

    Runs before create_all so a fresh DB can create the vector column, and adds
    the column to an already-existing transactions table (create_all never
    alters existing tables). Safe to call on every startup.
    """
    if not settings.database_url.startswith("postgresql"):
        return
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(
            text("ALTER TABLE IF EXISTS transactions ADD COLUMN IF NOT EXISTS embedding vector(1536)")
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
