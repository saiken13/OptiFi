from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models.card import Card
from models.membership import Membership
from services.purchase_optimizer import PurchaseOptimizerService
from .base_agent import BaseAgent


class PurchaseAgent(BaseAgent):
    async def run(self, user_id: str, message: str, context: dict) -> dict:
        query = context.get("query") or message

        cards_q = await self.db.execute(
            select(Card)
            .options(selectinload(Card.reward_rules))
            .where(Card.user_id == user_id, Card.is_active == True)
        )
        cards = cards_q.scalars().all()

        memberships_q = await self.db.execute(
            select(Membership).where(
                Membership.user_id == user_id, Membership.is_active == True
            )
        )
        memberships = memberships_q.scalars().all()

        service = PurchaseOptimizerService()
        result = await service.optimize(
            query=query,
            cards=cards,
            memberships=memberships,
        )

        response = await self.format_response(
            result,
            user_context=f"User wants to buy: {query}"
        )
        return {"response": response, "structured_data": result}
