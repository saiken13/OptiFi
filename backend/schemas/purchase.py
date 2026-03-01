from pydantic import BaseModel
from typing import Optional


class PurchaseSearchRequest(BaseModel):
    query: str  # product name or URL


class PurchaseOptimizeRequest(BaseModel):
    query: str
    budget: Optional[float] = None


class MerchantResult(BaseModel):
    merchant: str
    price: float
    shipping: float
    url: str
    in_stock: bool = True
    membership_discount: float = 0.0
    membership_name: Optional[str] = None


class CardOptimization(BaseModel):
    card_id: str
    card_name: str
    cashback_rate: float
    cashback_amount: float
    rule_category: str
    evidence: Optional[str] = None


class OptimizedOption(BaseModel):
    rank: int
    merchant: str
    price: float
    shipping: float
    shipping_after_membership: float
    membership_savings: float
    best_card_id: Optional[str]
    best_card_name: Optional[str]
    cashback_amount: float
    net_cost: float
    total_savings: float
    breakdown: str
    url: str


class PurchaseOptimizeResponse(BaseModel):
    query: str
    best_option: OptimizedOption
    alternatives: list[OptimizedOption]
    all_options: list[OptimizedOption]
