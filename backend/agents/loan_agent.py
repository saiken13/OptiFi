from sqlalchemy import select
from models.loan import Loan
from utils.helpers import loan_amortization
from .base_agent import BaseAgent


class LoanAgent(BaseAgent):
    async def run(self, user_id: str, message: str, context: dict) -> dict:
        await self._extract_and_save_financial_data(user_id, message)

        loans_q = await self.db.execute(select(Loan).where(Loan.user_id == user_id))
        loans = loans_q.scalars().all()

        loans_analysis = []
        for loan in loans:
            schedule_standard = loan_amortization(
                float(loan.current_balance),
                float(loan.interest_rate),
                float(loan.monthly_payment),
                extra=0.0,
            )
            schedule_extra = loan_amortization(
                float(loan.current_balance),
                float(loan.interest_rate),
                float(loan.monthly_payment),
                extra=float(loan.extra_payment),
            ) if float(loan.extra_payment) > 0 else schedule_standard

            total_interest_standard = sum(m["interest"] for m in schedule_standard)
            total_interest_extra = sum(m["interest"] for m in schedule_extra)
            months_saved = len(schedule_standard) - len(schedule_extra)
            interest_saved = round(total_interest_standard - total_interest_extra, 2)

            loans_analysis.append({
                "name": loan.name,
                "type": loan.loan_type,
                "current_balance": float(loan.current_balance),
                "interest_rate": float(loan.interest_rate),
                "monthly_payment": float(loan.monthly_payment),
                "extra_payment": float(loan.extra_payment),
                "payoff_months_standard": len(schedule_standard),
                "payoff_months_with_extra": len(schedule_extra),
                "months_saved": months_saved,
                "total_interest_standard": round(total_interest_standard, 2),
                "total_interest_with_extra": round(total_interest_extra, 2),
                "interest_saved": interest_saved,
                "first_12_months": schedule_standard[:12],
            })

        total_debt = sum(float(l.current_balance) for l in loans)
        sorted_by_rate = sorted(loans, key=lambda l: float(l.interest_rate), reverse=True)
        sorted_by_balance = sorted(loans, key=lambda l: float(l.current_balance))

        tool_output = {
            "total_debt": round(total_debt, 2),
            "loan_count": len(loans),
            "loans": loans_analysis,
            "avalanche_order": [l.name for l in sorted_by_rate],
            "snowball_order": [l.name for l in sorted_by_balance],
            "strategy_recommendation": (
                "avalanche" if any(float(l.interest_rate) > 10 for l in loans) else "snowball"
            ),
        }

        response = await self.format_response(tool_output, user_context=f"User asked: {message}")
        return {"response": response, "structured_data": tool_output}
