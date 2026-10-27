import json
import unittest
import uuid
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from agents.goal_agent import GoalAgent, GoalPlan
from agents.orchestrator import Orchestrator, keyword_route
from services.goal_contribution_service import record_goal_contribution


class GoalContributionTests(unittest.IsolatedAsyncioTestCase):
    def setup_contribution(self, **fields):
        self.goal = SimpleNamespace(
            id=uuid.uuid4(), name="Car Fund", user_id="user-1", status="active",
            target_amount=Decimal("20000"), current_amount=Decimal("0"),
            monthly_contribution=Decimal("500"), target_date=date(2028, 10, 27),
        )
        self.goal_result = MagicMock()
        self.goal_result.scalar_one_or_none.return_value = self.goal
        self.duplicate_result = MagicMock()
        self.duplicate_result.scalar_one_or_none.return_value = None
        self.db = MagicMock()
        self.db.execute = AsyncMock(side_effect=[self.goal_result, self.duplicate_result])
        self.db.flush = AsyncMock()
        self.plan = GoalPlan(action="contribute", name="Car Fund", contribution_amount="1500", **fields)

    async def test_adds_savings_to_progress_not_target_or_recurring_setting(self):
        self.setup_contribution()
        result = await record_goal_contribution(self.db, "user-1", self.plan, [self.goal])
        self.assertEqual(self.goal.current_amount, Decimal("1500"))
        self.assertEqual(self.goal.target_amount, Decimal("20000"))
        self.assertEqual(self.goal.monthly_contribution, Decimal("500"))
        self.assertEqual(result["structured_data"]["percent_complete"], 7.5)
        self.assertEqual(result["structured_data"]["goal_action"], "contribution_recorded")
        self.db.add.assert_not_called()  # Savings allocation is not income or an expense.
        self.db.flush.assert_awaited_once()
        query = self.db.execute.call_args_list[0].args[0]
        self.assertIn("user-1", query.compile().params.values())
        self.assertIn("FOR UPDATE", str(query))

    async def test_adds_to_existing_balance_using_decimal_cents(self):
        self.setup_contribution()
        self.goal.current_amount = Decimal("200.15")
        self.plan.contribution_amount = Decimal("1500.10")
        await record_goal_contribution(self.db, "user-1", self.plan, [self.goal])
        self.assertEqual(self.goal.current_amount, Decimal("1700.25"))

    async def test_duplicate_receipt_does_not_increment_again(self):
        self.setup_contribution()
        self.duplicate_result.scalar_one_or_none.return_value = object()
        result = await record_goal_contribution(self.db, "user-1", self.plan, [self.goal])
        self.assertEqual(result["structured_data"]["goal_action"], "already_recorded")
        self.assertEqual(self.goal.current_amount, 0)
        self.db.flush.assert_not_awaited()

    async def test_ambiguous_goal_asks_without_changing_any_goal(self):
        self.setup_contribution()
        self.plan.name = "Savings Goal"
        result = await record_goal_contribution(self.db, "user-1", self.plan, [self.goal])
        self.assertEqual(result["structured_data"]["goal_action"], "needs_contribution_details")
        self.assertIn("Car Fund", result["response"])
        self.db.execute.assert_not_awaited()

    async def test_missing_goal_does_not_create_a_1500_dollar_target(self):
        self.setup_contribution()
        result = await record_goal_contribution(self.db, "user-1", self.plan, [])
        self.assertIn("create a goal", result["response"])
        self.db.add.assert_not_called()
        self.db.execute.assert_not_awaited()

    async def test_future_savings_do_not_change_progress(self):
        self.setup_contribution(contribution_date=date.today() + timedelta(days=1))
        result = await record_goal_contribution(self.db, "user-1", self.plan, [self.goal])
        self.assertEqual(result["structured_data"]["goal_action"], "needs_contribution_details")
        self.assertEqual(self.goal.current_amount, 0)

    async def test_failed_flush_does_not_confirm_success(self):
        self.setup_contribution()
        self.db.flush.side_effect = RuntimeError("database failure")
        with self.assertRaises(RuntimeError):
            await record_goal_contribution(self.db, "user-1", self.plan, [self.goal])

    async def test_goal_agent_handles_saved_amount_as_contribution(self):
        self.setup_contribution()
        available = MagicMock()
        available.scalars.return_value.all.return_value = [self.goal]
        self.db.execute.side_effect = [available, self.goal_result, self.duplicate_result]
        agent = object.__new__(GoalAgent)
        agent.db = self.db
        agent.ask_llm = AsyncMock(return_value=self.plan.model_dump_json())
        result = await agent.run("user-1", "I asaved $1500 this month for buying a car", {})
        self.assertEqual(result["structured_data"]["current_amount"], 1500)
        supplied = json.loads(agent.ask_llm.call_args.kwargs["user"])
        self.assertEqual(supplied["available_goals"], [{"name": "Car Fund"}])

    async def test_invalid_amount_is_visible_without_mutation(self):
        self.setup_contribution()
        available = MagicMock()
        available.scalars.return_value.all.return_value = [self.goal]
        self.db.execute.side_effect = [available]
        agent = object.__new__(GoalAgent)
        agent.db = self.db
        agent.ask_llm = AsyncMock(return_value='{"action":"contribute","name":"Car Fund","contribution_amount":-100}')
        with self.assertRaises(HTTPException):
            await agent.run("user-1", "I saved money for a car", {})
        self.assertEqual(self.goal.current_amount, 0)

    async def test_name_only_followup_resumes_pending_contribution(self):
        self.setup_contribution()
        self.db.execute = AsyncMock(return_value=MagicMock())
        pending = self.plan.model_dump(mode="json")
        self.db.execute.return_value.scalar_one_or_none.return_value = SimpleNamespace(structured_data={"pending_goal": pending})
        orchestrator = object.__new__(Orchestrator)
        orchestrator.db = self.db
        goal_agent = SimpleNamespace(run=AsyncMock(return_value={"response": "Saved", "structured_data": {}}))
        orchestrator.agents = {"goal": goal_agent, "general": None}
        await orchestrator.route("user-1", "Car Fund")
        self.assertEqual(goal_agent.run.call_args.kwargs["context"]["pending_goal"], pending)

    def test_saved_and_asaved_route_to_goals_before_shopping(self):
        self.assertEqual(keyword_route("I saved $1500 this month for buying a car"), "goal")
        self.assertEqual(keyword_route("I asaved $1500 this month for buying a car"), "goal")

    async def test_pending_goal_does_not_capture_explicit_loan_payment(self):
        self.setup_contribution()
        self.db.execute = AsyncMock(return_value=MagicMock())
        self.db.execute.return_value.scalar_one_or_none.return_value = SimpleNamespace(
            structured_data={"pending_goal": self.plan.model_dump(mode="json")})
        orchestrator = object.__new__(Orchestrator)
        orchestrator.db = self.db
        loan_agent = SimpleNamespace(run=AsyncMock(return_value={"response": "Payment", "structured_data": {}}))
        goal_agent = SimpleNamespace(run=AsyncMock())
        orchestrator.agents = {"loan": loan_agent, "goal": goal_agent, "general": None}
        await orchestrator.route("user-1", "I paid $1000 for my student loan")
        loan_agent.run.assert_awaited_once()
        goal_agent.run.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
