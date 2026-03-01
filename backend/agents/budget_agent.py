from datetime import date
from sqlalchemy import select, func, and_
from models.budget import Budget
from models.transaction import Transaction
from .base_agent import BaseAgent


class BudgetAgent(BaseAgent):
    async def run(self, user_id: str, message: str, context: dict) -> dict:
        await self._extract_and_save_financial_data(user_id, message)

        today = date.today()
        month, year = today.month, today.year

        budgets_q = await self.db.execute(
            select(Budget).where(
                and_(Budget.user_id == user_id, Budget.month == month, Budget.year == year)
            )
        )
        budgets = budgets_q.scalars().all()

        txns_q = await self.db.execute(
            select(Transaction).where(
                and_(
                    Transaction.user_id == user_id,
                    func.extract("month", Transaction.date) == month,
                    func.extract("year", Transaction.date) == year,
                )
            )
        )
        transactions = txns_q.scalars().all()

        spending_by_category: dict[str, float] = {}
        for t in transactions:
            cat = t.category or "uncategorized"
            spending_by_category[cat] = spending_by_category.get(cat, 0) + float(t.amount)

        budget_health = []
        total_budget = 0.0
        total_spent = 0.0
        for b in budgets:
            spent = spending_by_category.get(b.category, 0)
            pct = (spent / float(b.monthly_limit) * 100) if b.monthly_limit > 0 else 0
            budget_health.append({
                "category": b.category,
                "limit": float(b.monthly_limit),
                "spent": round(spent, 2),
                "remaining": round(float(b.monthly_limit) - spent, 2),
                "percent_used": round(pct, 1),
                "status": "over" if pct > 100 else ("warning" if pct > 80 else "ok"),
            })
            total_budget += float(b.monthly_limit)
            total_spent += spent

        tool_output = {
            "month": f"{today.strftime('%B')} {year}",
            "total_budget": round(total_budget, 2),
            "total_spent": round(total_spent, 2),
            "total_remaining": round(total_budget - total_spent, 2),
            "budget_health": budget_health,
            "uncategorized_spending": spending_by_category.get("uncategorized", 0),
        }

        response = await self.format_response(
            tool_output,
            user_context=f"User asked: {message}"
        )

        return {"response": response, "structured_data": tool_output}
