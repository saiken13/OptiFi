from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from models.card import Card
from models.membership import Membership
from schemas.purchase import PurchaseOptimizeRequest, PurchaseOptimizeResponse
from utils.security import get_current_user_id
from services.purchase_optimizer import PurchaseOptimizerService

router = APIRouter(prefix="/purchase", tags=["purchase"])


@router.post("/optimize")
async def optimize_purchase(
    body: PurchaseOptimizeRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    cards_q = await db.execute(
        select(Card).options(selectinload(Card.reward_rules)).where(Card.user_id == user_id, Card.is_active == True)
    )
    cards = cards_q.scalars().all()

    memberships_q = await db.execute(
        select(Membership).where(Membership.user_id == user_id, Membership.is_active == True)
    )
    memberships = memberships_q.scalars().all()

    service = PurchaseOptimizerService()
    result = await service.optimize(query=body.query, cards=cards, memberships=memberships)
    return result


@router.post("/search")
async def search_products(
    body: PurchaseOptimizeRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    service = PurchaseOptimizerService()
    products = await service._search_products(body.query)
    return {"results": products}
