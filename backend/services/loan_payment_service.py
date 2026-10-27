"""Record explicit loan payments without inferring an interest allocation."""
import json
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated, Literal, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from models.loan import Loan
from models.transaction import Transaction


class PaymentPlan(BaseModel):
    action: Literal["payment", "cancel", "none", "create"]
    loan_name: Optional[str] = None
    loan_type: Optional[Literal["student", "mortgage", "auto", "personal", "credit_card"]] = None
    amount: Optional[Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]] = None
    principal_amount: Optional[Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]] = None
    remaining_balance: Optional[Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]] = None
    payment_date: Optional[date] = None


PAYMENT_PROMPT = """Extract a COMPLETED loan payment from the user's current message.
Return ONLY JSON: action (payment, cancel, none, create), loan_name, loan_type,
amount (total paid), principal_amount, remaining_balance, payment_date (YYYY-MM-DD).
Use null for missing details. Only extract explicit user facts; never calculate interest or guess principal.
"paid $1000 for student loan this month" means amount 1000, loan_type student,
principal_amount null, remaining_balance null. A payment total is NOT necessarily principal.
"all of it went to principal" explicitly assigns the pending total to principal_amount.
"my balance is now $24000" supplies remaining_balance, not principal_amount.
Questions, hypothetical payments, future intentions, and recurring monthly payment settings are action none.
A statement declaring a newly taken/borrowed loan is action create, even if it includes monthly payment terms.
Only a completed payment or an answer to the pending payment's clarification is action payment.
Continue relevant fields from pending_payment, but only if the current reply answers it.
Use explicit loan names only; do not invent a name or choose between multiple loans.
Use the supplied recording date when the payment date is unspecified.
Cancel means abandoning the pending request, not reversing a recorded payment."""


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def needs_payment_check(message: str, context: dict) -> bool:
    return bool(context.get("pending_loan_payment") or re.search(
        r"\b(?:paid|repaid|payment|payments|paying)\b", message, re.I
    ))


class LoanPaymentService:
    def __init__(self, db, ask_llm):
        self.db = db
        self.ask_llm = ask_llm

    async def handle(self, user_id: str, message: str, context: dict):
        if not needs_payment_check(message, context):
            return None
        pending = context.get("pending_loan_payment")
        raw = await self.ask_llm(
            system=PAYMENT_PROMPT,
            user=json.dumps({"recording_date": date.today().isoformat(), "pending_payment": pending, "message": message}),
            max_tokens=1200,
        )
        try:
            if "```" in raw:
                raw = raw.split("```")[1].removeprefix("json")
            plan = PaymentPlan.model_validate_json(raw.strip())
        except ValueError as exc:
            raise HTTPException(503, "I couldn't read the payment details. No payment was recorded; please retry.") from exc
        if plan.action == "create":
            return None
        if plan.action == "none":
            return {"analysis_only": True}
        if plan.action == "cancel":
            return {"response": "Cancelled the pending payment request. No loan balance was changed.", "structured_data": {"loan_action": "cancelled"}}

        # Lock this user's loan rows so concurrent payment requests cannot lose balance changes.
        loans = (await self.db.execute(
            select(Loan).where(Loan.user_id == user_id).order_by(Loan.id).with_for_update()
        )).scalars().all()
        candidates = loans
        if plan.loan_name:
            candidates = [loan for loan in candidates if loan.name.casefold() == plan.loan_name.casefold()]
        if plan.loan_type:
            candidates = [loan for loan in candidates if loan.loan_type == plan.loan_type]

        def clarify(question):
            return {
                "response": question + " No payment has been recorded yet.",
                "structured_data": {"loan_action": "needs_details", "pending_loan_payment": plan.model_dump(mode="json")},
            }

        if not candidates:
            return clarify("I couldn't find a matching loan. What is the exact name of the loan in your Loans page?")
        if len(candidates) > 1:
            names = ", ".join(loan.name for loan in candidates)
            return clarify(f"Which loan did you pay? Please give its exact name: {names}.")
        loan = candidates[0]
        # Pin subsequent clarifications to this loan rather than selecting a different one.
        plan.loan_name, plan.loan_type = loan.name, loan.loan_type
        if plan.amount is None:
            return clarify(f"How much did you pay toward {loan.name} in total?")
        if plan.principal_amount is None and plan.remaining_balance is None:
            return clarify(
                f"Of the ${plan.amount:,.2f} paid toward {loan.name}, how much went to principal, "
                "or what remaining balance does your lender show? If it was entirely principal, say 'all principal'."
            )

        before = money(loan.current_balance)
        principal = money(plan.principal_amount) if plan.principal_amount is not None else before - money(plan.remaining_balance)
        after = before - principal
        if principal < 0 or principal > plan.amount or after < 0:
            return clarify("Those figures don't match the current loan balance and payment. Please provide the principal paid and total payment shown by your lender.")
        if plan.remaining_balance is not None and after != money(plan.remaining_balance):
            return clarify("The supplied principal and remaining balance disagree. Please check the lender's figures.")
        payment_date = plan.payment_date or date.today()
        if payment_date > date.today():
            return clarify("That date is in the future. What was the date of the completed payment?")

        account = f"loan:{loan.id}"
        # Guard against accidentally re-entering the same payment after a lost response.
        duplicate = (await self.db.execute(select(Transaction).where(
            Transaction.user_id == user_id, Transaction.account == account,
            Transaction.category == "loan_payment", Transaction.date == payment_date,
            Transaction.amount == -plan.amount,
        ))).scalars().first()
        if duplicate:
            return {
                "response": f"A ${plan.amount:,.2f} payment for {loan.name} on {payment_date} is already recorded. I haven't reduced the balance again. If this was a separate payment, record it separately after checking your history.",
                "structured_data": {"loan_action": "already_recorded", "loan_id": str(loan.id)},
            }

        loan.current_balance = after
        transaction = Transaction(
            user_id=user_id, date=payment_date, amount=-plan.amount,
            category="loan_payment", account=account,
            description=f"Payment toward {loan.name}; principal ${principal:.2f}; balance ${before:.2f} -> ${after:.2f}",
        )
        self.db.add(transaction)
        # Both changes are committed together by get_db; an error rolls both back.
        await self.db.flush()
        total_debt = sum((money(item.current_balance) for item in loans), Decimal("0.00"))
        return {
            "response": (
                f"Recorded your ${plan.amount:,.2f} payment toward {loan.name} on {payment_date}. "
                f"Principal reduced by ${principal:,.2f}; the balance changed from ${before:,.2f} to ${after:,.2f}. "
                f"Your total debt is now ${total_debt:,.2f}. Your regular monthly payment setting is unchanged."
            ),
            "structured_data": {
                "loan_action": "payment_recorded", "loan_id": str(loan.id),
                "amount": float(plan.amount), "principal_amount": float(principal),
                "previous_balance": float(before), "current_balance": float(after),
                "total_debt": float(total_debt), "payment_date": payment_date.isoformat(),
            },
        }
