from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---- Auth ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(default="", max_length=120)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- Accounts ----
class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    type: str = Field(default="checking", max_length=32)
    institution: str = Field(default="", max_length=120)


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    institution: str
    created_at: datetime


# ---- Transactions ----
class TransactionCreate(BaseModel):
    date: date
    description: str = Field(..., min_length=1, max_length=255)
    amount: float
    category: str | None = Field(default=None, max_length=64)
    account_id: int | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    description: str
    amount: float
    category: str
    account_id: int | None
    statement_id: int | None


# ---- Uploads ----
class UploadResult(BaseModel):
    statement_id: int
    filename: str
    imported: int
    account_id: int | None


# ---- Insights ----
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
