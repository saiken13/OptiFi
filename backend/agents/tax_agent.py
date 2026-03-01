from datetime import date
from sqlalchemy import select, extract, and_
from models.transaction import Transaction
from models.loan import Loan
from .base_agent import BaseAgent

_TAX_SYSTEM = """You are a US tax advisor AI. Given the user's transaction data, loans, and financial summary, identify potential tax deductions and savings opportunities.

Analyze the data and return ONLY valid JSON in this exact format:
{
  "deductions": [
    {
      "category": "Medical Expenses",
      "description": "Health-related spending may be deductible if over 7.5% of AGI",
      "estimated_amount": 450.00,
      "deduction_type": "itemized",
      "confidence": "possible",
      "notes": "Keep receipts for all medical expenses"
    }
  ],
  "tax_saving_strategies": [
    "Max out your 401(k) contribution to reduce taxable income",
    "Consider an HSA if you have a high-deductible health plan"
  ],
  "estimated_total_deductions": 1200.00,
  "estimated_tax_savings": 264.00,
  "assumed_tax_rate": 22,
  "disclaimer": "Consult a CPA for personalized tax advice."
}

Deduction types: itemized, above_the_line, business, education
Confidence levels: likely, possible, unlikely

Common deductible categories to look for:
- health/medical spending → medical expense deduction (above 7.5% AGI threshold)
- home office → utilities, subscriptions if WFH
- student loan interest → from loan data (above-the-line deduction, up to $2500)
- mortgage interest → from loan data
- charitable donations → look for keywords like "charity", "donation", "church", "nonprofit"
- education → courses, books, tuition
- business meals → dining if business-related (50% deductible)
- vehicle/mileage → gas if business use

Only include deductions that are realistically applicable. Do not fabricate data."""


class TaxAgent(BaseAgent):
    async def run(self, user_id: str, message: str, context: dict) -> dict:
        today = date.today()
        tax_year = context.get("tax_year", today.year - 1 if today.month < 4 else today.year)

        # Fetch all transactions for the tax year
        txns_q = await self.db.execute(
            select(Transaction).where(
                and_(
                    Transaction.user_id == user_id,
                    extract("year", Transaction.date) == tax_year,
                )
            )
        )
        transactions = txns_q.scalars().all()

        # Fetch loans (mortgage interest, student loan)
        loans_q = await self.db.execute(select(Loan).where(Loan.user_id == user_id))
        loans = loans_q.scalars().all()

        # Summarize spending by category
        category_totals: dict[str, float] = {}
        total_expenses = 0.0
        total_income = 0.0
        notable_txns: list[str] = []

        for t in transactions:
            amt = float(t.amount)
            if amt < 0:
                total_expenses += abs(amt)
                cat = t.category or "other"
                category_totals[cat] = category_totals.get(cat, 0) + abs(amt)
                # Flag notable descriptions for AI analysis
                desc_lower = t.description.lower()
                if any(kw in desc_lower for kw in [
                    "charity", "donat", "church", "nonprofit", "school", "tuition",
                    "course", "medical", "doctor", "hospital", "pharmacy", "dental",
                    "home office", "business"
                ]):
                    notable_txns.append(f"{t.date}: {t.description} (${abs(amt):.2f})")
            else:
                total_income += amt

        loan_summary = []
        for l in loans:
            yearly_interest = float(l.current_balance) * (float(l.interest_rate) / 100)
            loan_summary.append({
                "name": l.name,
                "type": l.loan_type,
                "balance": float(l.current_balance),
                "rate": float(l.interest_rate),
                "est_yearly_interest": round(yearly_interest, 2),
            })

        data_for_llm = {
            "tax_year": tax_year,
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "spending_by_category": {k: round(v, 2) for k, v in category_totals.items()},
            "notable_transactions": notable_txns[:20],
            "loans": loan_summary,
            "transaction_count": len(transactions),
        }

        import json
        user_prompt = f"Here is the user's financial data for tax year {tax_year}:\n{json.dumps(data_for_llm, indent=2)}\n\nIdentify tax saving opportunities."

        try:
            raw = await self.ask_llm(system=_TAX_SYSTEM, user=user_prompt, max_tokens=1500)
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            structured = json.loads(raw.strip())
        except Exception:
            structured = {
                "deductions": [],
                "tax_saving_strategies": ["Unable to analyze — please try again."],
                "estimated_total_deductions": 0.0,
                "estimated_tax_savings": 0.0,
                "assumed_tax_rate": 22,
                "disclaimer": "Consult a CPA for personalized tax advice.",
            }

        narrative_prompt = f"""
Tax year: {tax_year}
User income: ${total_income:,.2f}, expenses: ${total_expenses:,.2f}
Identified deductions: {json.dumps(structured.get('deductions', []), indent=2)}
Strategies: {structured.get('tax_saving_strategies', [])}
Estimated savings: ${structured.get('estimated_tax_savings', 0):,.2f}

Write a friendly, concise (3-4 paragraph) tax savings summary for this user.
Mention the most impactful deductions, how much they could save, and 2-3 actionable next steps.
End with a reminder to consult a tax professional.
"""
        narrative = await self.format_response(
            {"narrative_prompt": narrative_prompt},
            user_context=f"Generate a tax savings narrative for {tax_year}"
        )

        return {
            "response": narrative,
            "structured_data": {
                **structured,
                "tax_year": tax_year,
                "data_summary": data_for_llm,
            },
        }
