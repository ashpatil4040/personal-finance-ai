import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATA_DIR = os.environ.get(
    "PFAI_DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
)
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = os.environ.get(
    "PFAI_DATABASE_URL", f"sqlite:///{os.path.join(DATA_DIR, 'finance.db')}"
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
