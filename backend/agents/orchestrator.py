import time
import re
from typing import Optional
from pathlib import Path
import groq
from database import settings

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
        if intent is None:
            intent = await llm_classify_intent(message)

        agent = self.agents.get(intent, self.agents["general"])
        result = await agent.run(user_id=user_id, message=message, context=context or {})

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "intent": intent,
            "response": result["response"],
            "structured_data": result.get("structured_data"),
            "processing_time_ms": elapsed_ms,
        }
