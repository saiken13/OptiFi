import json
import unittest
import uuid
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from agents.loan_agent import LoanAgent
from agents.orchestrator import Orchestrator
from models.transaction import Transaction
from services.loan_payment_service import LoanPaymentService


class LoanPaymentTests(unittest.IsolatedAsyncioTestCase):
    def setup_payment(self, **fields):
        self.loan = SimpleNamespace(
            id=uuid.uuid4(), user_id="user-1", name="Student Loan", loan_type="student",
            current_balance=Decimal("25000"), principal=Decimal("25000"),
            monthly_payment=Decimal("416.67"), interest_rate=Decimal("5.5"), extra_payment=Decimal("0"),
        )
        self.loans_result = MagicMock()
        self.loans_result.scalars.return_value.all.return_value = [self.loan]
        self.duplicate_result = MagicMock()
        self.duplicate_result.scalars.return_value.first.return_value = None
        self.db = MagicMock()
        self.db.execute = AsyncMock(side_effect=[self.loans_result, self.duplicate_result])
        self.db.flush = AsyncMock()
        self.plan = {"action": "payment", "loan_type": "student", "amount": 1000, **fields}
        self.extract = AsyncMock(return_value=json.dumps(self.plan))
        return LoanPaymentService(self.db, self.extract)

    async def test_total_alone_requests_principal_without_changing_balance(self):
        service = self.setup_payment()
        result = await service.handle("user-1", "paid $1000 for student loan this month", {})
        self.assertEqual(result["structured_data"]["loan_action"], "needs_details")
        self.assertEqual(result["structured_data"]["pending_loan_payment"]["loan_name"], "Student Loan")
        self.assertEqual(self.loan.current_balance, Decimal("25000"))
        self.db.add.assert_not_called()
        self.db.flush.assert_not_awaited()

    async def test_explicit_principal_updates_loan_and_creates_one_transaction(self):
        service = self.setup_payment(principal_amount="885.42")
        result = await service.handle("user-1", "paid $1000 for student loan, $885.42 principal", {})
        self.assertEqual(self.loan.current_balance, Decimal("24114.58"))
        self.assertEqual(self.loan.principal, Decimal("25000"))
        self.assertEqual(self.loan.monthly_payment, Decimal("416.67"))
        self.assertEqual(result["structured_data"]["total_debt"], 24114.58)
        transaction = self.db.add.call_args.args[0]
        self.assertIsInstance(transaction, Transaction)
        self.assertEqual(transaction.amount, Decimal("-1000"))
        self.assertEqual(transaction.user_id, "user-1")
        self.assertEqual(transaction.account, f"loan:{self.loan.id}")
        self.db.flush.assert_awaited_once()
        query = self.db.execute.call_args_list[0].args[0]
        self.assertIn("user-1", query.compile().params.values())
        self.assertIn("FOR UPDATE", str(query))

    async def test_lender_balance_sets_exact_remaining_debt(self):
        service = self.setup_payment(remaining_balance=24114.58)
        result = await service.handle("user-1", "paid $1000; student loan balance is now $24114.58", {})
        self.assertEqual(self.loan.current_balance, Decimal("24114.58"))
        self.assertEqual(result["structured_data"]["principal_amount"], 885.42)

    async def test_total_debt_includes_other_loans_without_changing_them(self):
        service = self.setup_payment(principal_amount=1000)
        other = SimpleNamespace(name="Car Loan", loan_type="auto", current_balance=Decimal("7000.25"))
        self.loans_result.scalars.return_value.all.return_value = [self.loan, other]
        result = await service.handle("user-1", "paid student loan", {})
        self.assertEqual(result["structured_data"]["total_debt"], 31000.25)
        self.assertEqual(other.current_balance, Decimal("7000.25"))

    async def test_loan_agent_returns_saved_payment_without_generated_claims(self):
        self.setup_payment(principal_amount=1000)
        agent = object.__new__(LoanAgent)
        agent.db = self.db
        agent.ask_llm = self.extract
        agent._extract_and_save_financial_data = AsyncMock()
        agent.format_response = AsyncMock()
        result = await agent.run("user-1", "paid $1000 for student loan, all principal", {})
        self.assertEqual(result["structured_data"]["loan_action"], "payment_recorded")
        self.assertEqual(self.loan.current_balance, Decimal("24000"))
        agent._extract_and_save_financial_data.assert_not_awaited()
        agent.format_response.assert_not_awaited()

    async def test_all_principal_followup_preserves_payment_context(self):
        service = self.setup_payment(principal_amount=1000, loan_name="Student Loan")
        pending = {"loan_name": "Student Loan", "loan_type": "student", "amount": "1000.00"}
        await service.handle("user-1", "all principal", {"pending_loan_payment": pending})
        self.assertEqual(self.loan.current_balance, Decimal("24000"))
        self.assertEqual(json.loads(self.extract.call_args.kwargs["user"])["pending_payment"], pending)

    async def test_multiple_student_loans_require_selection(self):
        service = self.setup_payment(principal_amount=1000)
        other = SimpleNamespace(name="Second Student Loan", loan_type="student")
        self.loans_result.scalars.return_value.all.return_value = [self.loan, other]
        result = await service.handle("user-1", "paid student loan", {})
        self.assertEqual(result["structured_data"]["loan_action"], "needs_details")
        self.assertIn("Which loan", result["response"])
        self.db.add.assert_not_called()

    async def test_no_matching_loan_does_not_create_phantom_loan(self):
        service = self.setup_payment(principal_amount=1000)
        self.loans_result.scalars.return_value.all.return_value = []
        result = await service.handle("user-1", "paid $1000 for student loan", {})
        self.assertIn("couldn't find", result["response"])
        self.db.add.assert_not_called()

    async def test_repeated_same_payment_is_not_deducted_twice(self):
        service = self.setup_payment(principal_amount=1000)
        self.duplicate_result.scalars.return_value.first.return_value = object()
        result = await service.handle("user-1", "paid $1000 for student loan", {})
        self.assertEqual(result["structured_data"]["loan_action"], "already_recorded")
        self.assertEqual(self.loan.current_balance, Decimal("25000"))
        self.db.add.assert_not_called()

    async def test_inconsistent_allocation_is_rejected(self):
        for fields in ({"principal_amount": 1500}, {"remaining_balance": 26000},
                       {"principal_amount": 1000, "remaining_balance": 24114.58}):
            with self.subTest(fields=fields):
                service = self.setup_payment(**fields)
                result = await service.handle("user-1", "paid student loan", {})
                self.assertEqual(result["structured_data"]["loan_action"], "needs_details")
                self.assertEqual(self.loan.current_balance, Decimal("25000"))
                self.db.add.assert_not_called()

    async def test_overpayment_does_not_make_balance_negative(self):
        service = self.setup_payment(amount=30000, principal_amount=30000)
        result = await service.handle("user-1", "paid student loan", {})
        self.assertEqual(result["structured_data"]["loan_action"], "needs_details")
        self.assertEqual(self.loan.current_balance, Decimal("25000"))

    async def test_future_payment_date_cannot_record_completed_payment(self):
        service = self.setup_payment(principal_amount=1000, payment_date=str(date.today() + timedelta(days=1)))
        result = await service.handle("user-1", "paid student loan", {})
        self.assertEqual(result["structured_data"]["loan_action"], "needs_details")
        self.db.add.assert_not_called()

    async def test_flush_failure_does_not_return_success(self):
        service = self.setup_payment(principal_amount=1000)
        self.db.flush.side_effect = RuntimeError("simulated database write failure")
        with self.assertRaises(RuntimeError):
            await service.handle("user-1", "paid student loan", {})

    async def test_malformed_model_output_does_not_silently_succeed(self):
        service = self.setup_payment()
        self.extract.return_value = "invalid JSON"
        with self.assertRaises(HTTPException):
            await service.handle("user-1", "paid student loan", {})
        self.db.execute.assert_not_awaited()

    async def test_hypothetical_payment_skips_generic_extractor(self):
        self.setup_payment(action="none")
        agent = object.__new__(LoanAgent)
        agent.db = self.db
        agent.ask_llm = self.extract
        agent._extract_and_save_financial_data = AsyncMock()
        agent.format_response = AsyncMock(return_value="Hypothetical analysis")
        await agent.run("user-1", "What if I paid $1000 toward my student loan?", {})
        agent._extract_and_save_financial_data.assert_not_awaited()
        self.db.add.assert_not_called()
        self.assertEqual(self.loan.current_balance, Decimal("25000"))

    async def test_orchestrator_loads_pending_payment_from_same_user(self):
        self.setup_payment()
        self.db.execute = AsyncMock(return_value=MagicMock())
        pending = {"amount": "1000", "loan_name": "Student Loan"}
        self.db.execute.return_value.scalar_one_or_none.return_value = SimpleNamespace(
            structured_data={"pending_loan_payment": pending})
        orchestrator = object.__new__(Orchestrator)
        orchestrator.db = self.db
        loan_agent = SimpleNamespace(run=AsyncMock(return_value={"response": "Recorded", "structured_data": {}}))
        orchestrator.agents = {"loan": loan_agent, "general": None}
        await orchestrator.route("user-1", "all principal", {"pending_loan_payment": {"loan_name": "untrusted"}})
        self.assertEqual(loan_agent.run.call_args.kwargs["context"]["pending_loan_payment"], pending)
        self.assertIn("user-1", self.db.execute.call_args.args[0].compile().params.values())


if __name__ == "__main__":
    unittest.main()
