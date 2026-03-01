from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float
    month: int
    year: int


class BudgetUpdate(BaseModel):
    monthly_limit: Optional[float] = None
    spent_this_month: Optional[float] = None


class BudgetResponse(BaseModel):
    id: UUID
    user_id: UUID
    category: str
    monthly_limit: float
    spent_this_month: float
    month: int
    year: int
    created_at: datetime

    model_config = {"from_attributes": True}
