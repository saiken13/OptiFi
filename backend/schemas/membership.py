from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, date


class MembershipCreate(BaseModel):
    name: str
    merchant: str
    annual_fee: float = 0.0
    benefits: Optional[dict] = None
    renewal_date: Optional[date] = None


class MembershipResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    merchant: str
    annual_fee: float
    benefits: Optional[dict]
    is_active: bool
    renewal_date: Optional[date]
    created_at: datetime

    model_config = {"from_attributes": True}
