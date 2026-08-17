from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TransactionBase(BaseModel):
    date: date
    description: str = Field(..., min_length=1, max_length=255)
    amount: float
    category: str | None = Field(default=None, max_length=64)


class TransactionCreate(TransactionBase):
    pass


class TransactionOut(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str


class CategorizeRequest(BaseModel):
    description: str = Field(..., min_length=1)
    amount: float | None = None


class CategorizeResponse(BaseModel):
    category: str


class Summary(BaseModel):
    total_income: float
    total_spending: float
    net: float
    savings_rate: float
    transaction_count: int


class CategoryAmount(BaseModel):
    category: str
    amount: float


class MonthlyAmount(BaseModel):
    month: str
    amount: float


class InsightsResponse(BaseModel):
    summary: Summary
    spending_by_category: list[CategoryAmount]
    monthly_spending: list[MonthlyAmount]
    insights: list[str]
