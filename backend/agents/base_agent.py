from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
from datetime import date
import json
import groq
from sqlalchemy import select, and_
from database import settings

_formatter_prompt: Optional[str] = None


def _load_formatter() -> str:
    global _formatter_prompt
    if _formatter_prompt is None:
        path = Path(__file__).parent.parent / "prompts" / "response_formatter.txt"
        _formatter_prompt = path.read_text()
    return _formatter_prompt


_EXTRACT_SYSTEM = """You are a financial data extractor. Extract financial data explicitly mentioned in the user's message.
Return ONLY valid JSON in this exact format:
{
  "loans": [{"name": "Loan Name", "loan_type": "student|mortgage|auto|personal|credit_card", "balance": 0.0, "interest_rate": 5.5, "monthly_payment": 0.0}],
  "goals": [{"name": "Goal Name", "target_amount": 0.0, "monthly_contribution": 0.0}],
  "budgets": [{"category": "general", "monthly_limit": 0.0}],
  "transactions": [{"description": "Short description", "amount": -50.0, "category": "dining", "date": "YYYY-MM-DD"}]
}

Rules:
- Use empty arrays [] if nothing of that type is mentioned.
- Default interest rates if not stated: student=5.5, mortgage=6.5, auto=7.0, personal=12.0, credit_card=22.0
- Default monthly_payment = balance / 60 if not stated.
- For monthly expenses without a category, use category "general".
- Only extract numbers that are explicitly mentioned by the user.
- For transactions: amount is NEGATIVE for any spending/expense, POSITIVE for income.
- Use today's date (format YYYY-MM-DD) if no date is mentioned.
- Valid transaction categories: dining, groceries, gas, travel, shopping, entertainment, health, utilities, subscriptions, other.
- TRANSACTION EXAMPLES:
  "I spent $70 on dining" → [{"description": "Dining expense", "amount": -70.0, "category": "dining"}]
  "I bought groceries for $45" → [{"description": "Grocery shopping", "amount": -45.0, "category": "groceries"}]
  "I paid $120 for electricity" → [{"description": "Electricity bill", "amount": -120.0, "category": "utilities"}]
  "I received my salary of $5000" → [{"description": "Salary", "amount": 5000.0, "category": "other"}]
- BUDGET vs TRANSACTION: "my budget for dining is $500/month" → budget (monthly_limit). "I spent $70 on dining" → transaction."""


class BaseAgent(ABC):
    def __init__(self, db):
        self.db = db
        self.client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    @abstractmethod
    async def run(self, user_id: str, message: str, context: dict) -> dict:
        pass

    async def _extract_and_save_financial_data(self, user_id: str, message: str) -> int:
        """Parse the user's message for financial data and persist to DB. Returns count saved."""
        from models.loan import Loan
        from models.goal import Goal
        from models.budget import Budget
        from models.transaction import Transaction

        try:
            user_prompt = f"Today's date: {today.strftime('%Y-%m-%d')}\n\nUser message: {message}"
            raw = await self.ask_llm(system=_EXTRACT_SYSTEM, user=user_prompt, max_tokens=700)
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
        except Exception:
            return 0

        saved = 0
        today = date.today()

        for loan_data in data.get("loans", []):
            balance = float(loan_data.get("balance", 0))
            if balance <= 0:
                continue
            existing = (await self.db.execute(
                select(Loan).where(Loan.user_id == user_id, Loan.name == loan_data.get("name", ""))
            )).scalar_one_or_none()
            if existing:
                continue
            monthly_payment = float(loan_data.get("monthly_payment", 0)) or round(balance / 60, 2)
            loan = Loan(
                user_id=user_id,
                name=loan_data.get("name", "Loan"),
                loan_type=loan_data.get("loan_type", "personal"),
                principal=balance,
                current_balance=balance,
                interest_rate=float(loan_data.get("interest_rate", 10.0)),
                monthly_payment=monthly_payment,
                extra_payment=0.0,
            )
            self.db.add(loan)
            saved += 1

        for goal_data in data.get("goals", []):
            target = float(goal_data.get("target_amount", 0))
            if target <= 0:
                continue
            existing = (await self.db.execute(
                select(Goal).where(Goal.user_id == user_id, Goal.name == goal_data.get("name", ""))
            )).scalar_one_or_none()
            if existing:
                continue
            goal = Goal(
                user_id=user_id,
                name=goal_data.get("name", "Savings Goal"),
                target_amount=target,
                current_amount=0.0,
                monthly_contribution=float(goal_data.get("monthly_contribution", 0)),
                status="active",
            )
            self.db.add(goal)
            saved += 1

        for budget_data in data.get("budgets", []):
            limit = float(budget_data.get("monthly_limit", 0))
            if limit <= 0:
                continue
            category = budget_data.get("category", "general")
            existing = (await self.db.execute(
                select(Budget).where(
                    and_(
                        Budget.user_id == user_id,
                        Budget.category == category,
                        Budget.month == today.month,
                        Budget.year == today.year,
                    )
                )
            )).scalar_one_or_none()
            if existing:
                continue
            budget = Budget(
                user_id=user_id,
                category=category,
                monthly_limit=limit,
                spent_this_month=0.0,
                month=today.month,
                year=today.year,
            )
            self.db.add(budget)
            saved += 1

        for txn_data in data.get("transactions", []):
            amount = txn_data.get("amount")
            if amount is None:
                continue
            amount = float(amount)
            description = txn_data.get("description", "") or "Transaction"
            raw_date = txn_data.get("date", str(today))
            try:
                from datetime import datetime as dt
                txn_date = dt.strptime(raw_date[:10], "%Y-%m-%d").date()
            except Exception:
                txn_date = today
            category = txn_data.get("category") or None

            txn = Transaction(
                user_id=user_id,
                date=txn_date,
                description=description,
                amount=amount,
                category=category,
            )
            self.db.add(txn)
            saved += 1

            # If it's an expense, update the matching budget's spent_this_month
            if amount < 0 and category:
                budget_q = await self.db.execute(
                    select(Budget).where(
                        and_(
                            Budget.user_id == user_id,
                            Budget.category == category,
                            Budget.month == txn_date.month,
                            Budget.year == txn_date.year,
                        )
                    )
                )
                budget = budget_q.scalar_one_or_none()
                if budget:
                    budget.spent_this_month = float(budget.spent_this_month) + abs(amount)
                    self.db.add(budget)

        if saved > 0:
            await self.db.flush()
        return saved

    async def format_response(self, tool_output: dict, user_context: str = "") -> str:
        prompt = _load_formatter()
        prompt = prompt.replace("{tool_output}", json.dumps(tool_output, indent=2, default=str))
        prompt = prompt.replace("{user_context}", user_context)
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()

    async def ask_llm(self, system: str, user: str, max_tokens: int = 800) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content.strip()
