from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date


class TransactionCreate(BaseModel):
    date: date
    description: str
    amount: float
    category: Optional[str] = None
    merchant: Optional[str] = None


class TransactionResponse(BaseModel):
    id: UUID
    user_id: UUID
    date: date
    description: str
    amount: float
    category: Optional[str]
    merchant: Optional[str]
    account: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionSummary(BaseModel):
    total_income: float
    total_expenses: float
    net: float
    by_category: dict[str, float]
    top_merchants: list[dict]
    period_start: date
    period_end: date
