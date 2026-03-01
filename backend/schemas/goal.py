from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date


class GoalCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_amount: float
    current_amount: float = 0.0
    monthly_contribution: float = 0.0
    target_date: Optional[date] = None
    priority: int = 1


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    monthly_contribution: Optional[float] = None
    target_date: Optional[date] = None
    status: Optional[str] = None
    priority: Optional[int] = None


class GoalResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    target_amount: float
    current_amount: float
    monthly_contribution: float
    target_date: Optional[date]
    status: str
    priority: int
    created_at: datetime

    model_config = {"from_attributes": True}
