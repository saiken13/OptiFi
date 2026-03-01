from datetime import date
from sqlalchemy import select, and_, func
from models.transaction import Transaction
from models.goal import Goal
from models.loan import Loan
from models.budget import Budget
from utils.helpers import get_week_bounds
from .base_agent import BaseAgent


class WeeklyReviewAgent(BaseAgent):
    async def run(self, user_id: str, message: str, context: dict) -> dict:
        week_start, week_end = get_week_bounds()
        today = date.today()
        month, year = today.month, today.year

        txns_q = await self.db.execute(
            select(Transaction).where(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.date >= week_start,
                    Transaction.date <= week_end,
                )
            )
        )
        transactions = txns_q.scalars().all()

        budgets_q = await self.db.execute(
            select(Budget).where(
                and_(Budget.user_id == user_id, Budget.month == month, Budget.year == year)
            )
        )
        budgets = budgets_q.scalars().all()

        goals_q = await self.db.execute(
            select(Goal).where(Goal.user_id == user_id, Goal.status == "active")
        )
        goals = goals_q.scalars().all()

        loans_q = await self.db.execute(select(Loan).where(Loan.user_id == user_id))
        loans = loans_q.scalars().all()

        spending_by_category: dict[str, float] = {}
        total_expenses = 0.0
        total_income = 0.0
        for t in transactions:
            if float(t.amount) < 0:
                total_expenses += abs(float(t.amount))
                cat = t.category or "uncategorized"
                spending_by_category[cat] = spending_by_category.get(cat, 0) + abs(float(t.amount))
            else:
                total_income += float(t.amount)

        budget_alerts = []
        for b in budgets:
            spent = spending_by_category.get(b.category, 0)
            pct = (spent / float(b.monthly_limit) * 100) if b.monthly_limit > 0 else 0
            if pct > 80:
                budget_alerts.append(f"{b.category}: {pct:.0f}% of monthly budget used")

        tool_output = {
            "week": f"{week_start} to {week_end}",
            "total_expenses_this_week": round(total_expenses, 2),
            "total_income_this_week": round(total_income, 2),
            "net_this_week": round(total_income - total_expenses, 2),
            "spending_by_category": {k: round(v, 2) for k, v in spending_by_category.items()},
            "transaction_count": len(transactions),
            "budget_warnings": budget_alerts,
            "active_goals": len(goals),
            "total_goal_progress": sum(float(g.current_amount) / float(g.target_amount) * 100 for g in goals if float(g.target_amount) > 0) / max(len(goals), 1),
            "total_debt": sum(float(l.current_balance) for l in loans),
        }

        response = await self.format_response(tool_output, user_context=f"User asked: {message}")
        return {"response": response, "structured_data": tool_output}
