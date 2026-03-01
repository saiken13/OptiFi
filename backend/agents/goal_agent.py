from sqlalchemy import select
from models.goal import Goal
from utils.helpers import calculate_months_to_goal, format_currency
from .base_agent import BaseAgent


class GoalAgent(BaseAgent):
    async def run(self, user_id: str, message: str, context: dict) -> dict:
        await self._extract_and_save_financial_data(user_id, message)

        goals_q = await self.db.execute(
            select(Goal).where(Goal.user_id == user_id, Goal.status == "active")
        )
        goals = goals_q.scalars().all()

        goals_analysis = []
        for g in goals:
            remaining = float(g.target_amount) - float(g.current_amount)
            months_to_goal = calculate_months_to_goal(
                float(g.target_amount), float(g.current_amount), float(g.monthly_contribution)
            )
            pct_complete = (float(g.current_amount) / float(g.target_amount) * 100) if g.target_amount > 0 else 0

            years = None
            months_rem = None
            if months_to_goal is not None:
                years = int(months_to_goal // 12)
                months_rem = int(months_to_goal % 12)

            goals_analysis.append({
                "name": g.name,
                "target": float(g.target_amount),
                "current": float(g.current_amount),
                "remaining": round(remaining, 2),
                "monthly_contribution": float(g.monthly_contribution),
                "percent_complete": round(pct_complete, 1),
                "months_to_goal": round(months_to_goal, 1) if months_to_goal else None,
                "eta": f"{years}y {months_rem}m" if years is not None else "N/A (no contribution set)",
                "target_date": str(g.target_date) if g.target_date else None,
                "on_track": months_to_goal is not None,
            })

        tool_output = {
            "total_goals": len(goals),
            "goals": goals_analysis,
            "total_saved": sum(float(g.current_amount) for g in goals),
            "total_targets": sum(float(g.target_amount) for g in goals),
        }

        response = await self.format_response(tool_output, user_context=f"User asked: {message}")
        return {"response": response, "structured_data": tool_output}
