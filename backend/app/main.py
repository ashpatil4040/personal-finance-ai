from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import ai, schemas
from .database import Base, engine, get_db
from .models import Transaction

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Finance AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/transactions", response_model=list[schemas.TransactionOut])
def list_transactions(db: Session = Depends(get_db)):
    return (
        db.query(Transaction)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .all()
    )


@app.post("/api/transactions", response_model=schemas.TransactionOut, status_code=201)
def create_transaction(payload: schemas.TransactionCreate, db: Session = Depends(get_db)):
    category = payload.category or ai.categorize(payload.description, payload.amount)
    txn = Transaction(
        date=payload.date,
        description=payload.description,
        amount=payload.amount,
        category=category,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@app.delete("/api/transactions/{txn_id}", status_code=204)
def delete_transaction(txn_id: int, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(txn)
    db.commit()
    return None


@app.post("/api/categorize", response_model=schemas.CategorizeResponse)
def categorize_endpoint(payload: schemas.CategorizeRequest):
    return {"category": ai.categorize(payload.description, payload.amount)}


@app.get("/api/insights", response_model=schemas.InsightsResponse)
def insights(db: Session = Depends(get_db)):
    txns = db.query(Transaction).all()
    return ai.generate_insights(txns)
