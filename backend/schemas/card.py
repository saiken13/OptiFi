from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class CardRewardRuleCreate(BaseModel):
    rule_type: str
    category: str
    reward_rate: float
    cap_amount: Optional[float] = None
    cap_period: Optional[str] = None
    merchant_match: Optional[str] = None
    activation_required: bool = False
    evidence: Optional[str] = None
    source_url: Optional[str] = None


class CardCreate(BaseModel):
    name: str
    issuer: str
    last_four: Optional[str] = None
    network: Optional[str] = None
    annual_fee: float = 0.0


class CardRewardRuleResponse(BaseModel):
    id: UUID
    card_id: UUID
    rule_type: str
    category: str
    reward_rate: float
    cap_amount: Optional[float]
    cap_period: Optional[str]
    merchant_match: Optional[str]
    activation_required: bool
    evidence: Optional[str]
    source_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class CardResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    issuer: str
    last_four: Optional[str]
    network: Optional[str]
    annual_fee: float
    is_active: bool
    reward_rules: list[CardRewardRuleResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class CardImportSearchRequest(BaseModel):
    card_name: str
    issuer: str


class CardImportExtractRequest(BaseModel):
    job_id: str
    selected_url: str


class CardImportConfirmRequest(BaseModel):
    job_id: str
    card_name: str
    issuer: str
    rules: list[CardRewardRuleCreate]
