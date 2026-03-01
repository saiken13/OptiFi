from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date


class LoanCreate(BaseModel):
    name: str
    loan_type: str = "personal"
    principal: float
    current_balance: float
    interest_rate: float
    monthly_payment: float
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    extra_payment: float = 0.0


class LoanUpdate(BaseModel):
    name: Optional[str] = None
    current_balance: Optional[float] = None
    monthly_payment: Optional[float] = None
    extra_payment: Optional[float] = None
    interest_rate: Optional[float] = None


class LoanResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    loan_type: str
    principal: float
    current_balance: float
    interest_rate: float
    monthly_payment: float
    extra_payment: float
    start_date: Optional[date]
    end_date: Optional[date]
    created_at: datetime

    model_config = {"from_attributes": True}
