import json
import re
from typing import Literal, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models.card import Card
from models.membership import Membership
from services.purchase_optimizer import PurchaseOptimizerService
from .base_agent import BaseAgent


class ShoppingPlan(BaseModel):
    action: Literal["search", "cancel", "none"]
    query: str = Field(default="", max_length=500)
    budget: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)


SHOPPING_PROMPT = """Extract product shopping requirements. Return ONLY JSON:
action (search, cancel, none), query (specific product), budget (positive dollar amount or null).
Only use facts supplied by the user or the pending_purchase. Do not invent a budget, brand, model, price, or product type.
If the user only says bike, keep bike ambiguous: never assume bicycle or motorcycle.
Preserve pending requirements on a relevant follow-up; a budget-only reply supplies budget, not a new product.
If the user says bicycle or motorcycle on a follow-up, replace ambiguous bike with that type in query.
For relevant product requests action is search even when details are missing; application code asks for details.
Cancel abandons the pending search. Unrelated messages are none."""


class PurchaseAgent(BaseAgent):
    async def run(self, user_id: str, message: str, context: dict) -> dict:
        raw = await self.ask_llm(
            system=SHOPPING_PROMPT,
            user=json.dumps({"message": message, "pending_purchase": context.get("pending_purchase")}),
            max_tokens=1200,
        )
        try:
            if "```" in raw:
                raw = raw.split("```")[1].removeprefix("json")
            plan = ShoppingPlan.model_validate_json(raw.strip())
        except ValueError as exc:
            raise HTTPException(503, "I couldn't read the shopping details. Please retry; no product search was run.") from exc
        if plan.action == "cancel":
            return {"response": "Cancelled the pending product search.", "structured_data": {"purchase_action": "cancelled"}}
        if plan.action == "none":
            return {"response": "Would you like to plan a savings goal or compare products? Tell me what you want to do.", "structured_data": {"purchase_action": "needs_intent"}}
        questions = []
        query = plan.query.strip()
        if not query:
            questions.append("What product are you looking for?")
        if plan.budget is None:
            questions.append("What is your maximum purchase budget?")
        if re.search(r"\bbikes?\b", query, re.I) and not re.search(r"\b(?:bicycle|motorcycle|mountain|road|bmx|commuter|dirt)\b", query, re.I):
            questions.append("By bike, do you mean a bicycle or a motorcycle?")
        if questions:
            return {
                "response": " ".join(questions) + " I'll use those details before recommending any listings.",
                "structured_data": {"purchase_action": "needs_details", "pending_purchase": plan.model_dump(mode="json")},
            }

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
            budget=plan.budget,
        )

        if not result.get("best_option"):
            unavailable = result.get("data_status") == "sample_only"
            return {
                "response": ("I couldn't retrieve real product listings right now. Please try again later."
                             if unavailable else f"I found no listings within your ${plan.budget:,.2f} budget. Would you like to change the budget or product requirements?"),
                "structured_data": {**result, "purchase_action": "no_results", "pending_purchase": plan.model_dump(mode="json")},
            }

        response = await self.format_response(
            result,
            user_context=f"User wants to buy: {query}. Maximum upfront budget: ${plan.budget:.2f}. Use only the supplied listings and card rules. Do not invent prices, availability, shipping terms, or reward eligibility."
        )
        return {"response": response, "structured_data": result}
