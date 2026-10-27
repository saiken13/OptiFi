import time
import re
from typing import Optional
from pathlib import Path
import groq
from sqlalchemy import select
from database import settings
from models.message import Message

from .budget_agent import BudgetAgent
from .goal_agent import GoalAgent
from .loan_agent import LoanAgent
from .purchase_agent import PurchaseAgent
from .weekly_review_agent import WeeklyReviewAgent
from .general_agent import GeneralAgent

INTENT_KEYWORDS: dict[str, list[str]] = {
    "budget": ["budget", "spending", "overspent", "category limit", "monthly limit", "how much did i spend"],
    "goal": ["goal", "saving for", "savings goal", "target amount", "how long to save", "when will i reach"],
    "loan": ["loan", "debt", "pay off", "payoff", "mortgage", "student loan", "interest rate", "amortization", "avalanche", "snowball"],
    "weekly_review": ["weekly review", "this week", "last week", "weekly summary", "how did i do"],
    "purchase_optimize": ["buy", "purchase", "where should i", "best price", "which card", "cheapest", "shop", "order"],
    "card_import": ["import card", "add card", "credit card rewards", "add my card", "card rewards", "what rewards"],
    "tax": ["tax", "taxes", "deduction", "write off", "irs", "w-2", "1099"],
}

_intent_prompt: Optional[str] = None


def _load_intent_prompt() -> str:
    global _intent_prompt
    if _intent_prompt is None:
        path = Path(__file__).parent.parent / "prompts" / "intent_classifier.txt"
        _intent_prompt = path.read_text()
    return _intent_prompt


def keyword_route(message: str) -> Optional[str]:
    msg_lower = message.lower()
    future_purchase = re.search(r"\bplan(?:ning)?\b.*\b(?:buy|purchase)\b", msg_lower)
    shopping_request = re.search(r"\b(?:which card|best price|cheapest|compare|find deals|where should i|where can i)\b", msg_lower)
    saving_to_buy = re.search(r"\b(?:save|saved|saving|asaved)\b.*\b(?:buy\w*|purchase|car|goal)\b", msg_lower)
    if saving_to_buy or (future_purchase and not shopping_request):
        return "goal"
    if shopping_request:
        return "purchase_optimize"
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in msg_lower for kw in keywords):
            return intent
    return None


async def llm_classify_intent(message: str) -> str:
    client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)
    prompt = _load_intent_prompt().replace("{message}", message)
    response = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.choices[0].message.content.strip().lower()
    valid = {"budget", "goal", "loan", "tax", "weekly_review", "purchase_optimize", "card_import", "general"}
    return raw if raw in valid else "general"


class Orchestrator:
    def __init__(self, db):
        self.db = db
        self.agents = {
            "budget": BudgetAgent(db),
            "goal": GoalAgent(db),
            "loan": LoanAgent(db),
            "purchase_optimize": PurchaseAgent(db),
            "weekly_review": WeeklyReviewAgent(db),
            "general": GeneralAgent(db),
        }

    async def route(self, user_id: str, message: str, context: Optional[dict] = None) -> dict:
        start = time.monotonic()

        intent = keyword_route(message)
        context = dict(context or {})
        # Pending details come from the last saved assistant response, scoped to this user.
        context.pop("pending_goal", None)
        context.pop("pending_loan_payment", None)
        context.pop("pending_purchase", None)
        if intent in (None, "goal", "loan", "purchase_optimize", "budget"):
            previous = (await self.db.execute(
                select(Message).where(Message.user_id == user_id, Message.role == "assistant")
                .order_by(Message.created_at.desc()).limit(1)
            )).scalar_one_or_none()
            pending = (previous.structured_data or {}).get("pending_goal") if previous else None
            pending_payment = (previous.structured_data or {}).get("pending_loan_payment") if previous else None
            pending_purchase = (previous.structured_data or {}).get("pending_purchase") if previous else None
            budget_answer = intent == "budget" and re.search(r"\bbudget\b.*\d", message, re.I) and not re.search(r"\b(?:monthly|category|create|set|limit)\b", message, re.I)
            if pending_purchase and (intent in (None, "purchase_optimize") or budget_answer):
                context["pending_purchase"] = pending_purchase
                intent = "purchase_optimize"
            if pending_payment and intent in (None, "loan"):
                context["pending_loan_payment"] = pending_payment
                intent = "loan"
            if pending and (intent in (None, "goal") or budget_answer):
                context["pending_goal"] = pending
                intent = "goal"
        if intent is None:
            intent = await llm_classify_intent(message)

        agent = self.agents.get(intent, self.agents["general"])
        result = await agent.run(user_id=user_id, message=message, context=context)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "intent": intent,
            "response": result["response"],
            "structured_data": result.get("structured_data"),
            "processing_time_ms": elapsed_ms,
        }
