import json
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from agents.goal_agent import GoalAgent
from agents.orchestrator import Orchestrator, keyword_route


class GoalChatTests(unittest.IsolatedAsyncioTestCase):
    def agent(self, plan):
        db = MagicMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock())
        db.execute.return_value.scalars.return_value.first.return_value = None
        agent = object.__new__(GoalAgent)
        agent.db = db
        agent.ask_llm = AsyncMock(return_value=json.dumps(plan))
        return agent

    async def test_missing_amount_asks_without_creating_or_inventing_money(self):
        agent = self.agent({"action": "create", "name": "Car", "target_date": "2028-10-26"})
        result = await agent.run("user-1", "Planning to buy a car in 2 years", {})
        self.assertEqual(result["structured_data"]["goal_action"], "needs_target_amount")
        self.assertIsNone(result["structured_data"]["pending_goal"]["target_amount"])
        self.assertEqual(result["structured_data"]["pending_goal"]["target_date"], "2028-10-26")
        agent.db.add.assert_not_called()
        self.assertIn("haven't created", result["response"])

    async def test_amount_followup_creates_goal_with_preserved_deadline(self):
        pending = {"name": "Car", "target_date": "2028-10-26", "target_amount": None}
        agent = self.agent({"action": "create", "name": "Car", "target_date": "2028-10-26", "target_amount": 25000})
        result = await agent.run("user-1", "$25000", {"pending_goal": pending})
        goal = agent.db.add.call_args.args[0]
        self.assertEqual(goal.user_id, "user-1")
        self.assertEqual(goal.target_amount, 25000)
        self.assertEqual(goal.target_date, date(2028, 10, 26))
        agent.db.flush.assert_awaited_once()
        self.assertEqual(result["structured_data"]["goal_action"], "created")
        supplied = json.loads(agent.ask_llm.call_args.kwargs["user"])
        self.assertEqual(supplied["pending_goal"], pending)

    async def test_invalid_extraction_does_not_silently_give_advice(self):
        agent = self.agent({})
        agent.ask_llm.return_value = "not JSON"
        with self.assertRaises(HTTPException) as error:
            await agent.run("user-1", "Create a car goal", {})
        self.assertEqual(error.exception.status_code, 503)
        agent.db.add.assert_not_called()

    async def test_repeat_does_not_create_duplicate(self):
        agent = self.agent({"action": "create", "name": "Car", "target_amount": 25000})
        agent.db.execute.return_value.scalars.return_value.first.return_value = SimpleNamespace(name="Car")
        result = await agent.run("user-1", "Create a car goal for $25000", {})
        self.assertEqual(result["structured_data"]["goal_action"], "already_exists")
        agent.db.add.assert_not_called()

    async def test_goal_question_does_not_create(self):
        agent = self.agent({"action": "none"})
        agent.db.execute.return_value.scalars.return_value.all.return_value = []
        agent.format_response = AsyncMock(return_value="No goals yet")
        await agent.run("user-1", "How are my goals doing?", {})
        agent.db.add.assert_not_called()

    async def test_orchestrator_resumes_saved_pending_goal(self):
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock())
        pending = {"name": "Car", "target_date": "2028-10-26"}
        db.execute.return_value.scalar_one_or_none.return_value = SimpleNamespace(structured_data={"pending_goal": pending})
        orchestrator = object.__new__(Orchestrator)
        orchestrator.db = db
        goal_agent = SimpleNamespace(run=AsyncMock(return_value={"response": "Created", "structured_data": {}}))
        orchestrator.agents = {"goal": goal_agent, "general": None}
        await orchestrator.route("user-1", "$25000", {"pending_goal": {"name": "untrusted"}})
        self.assertEqual(goal_agent.run.call_args.kwargs["context"]["pending_goal"], pending)
        query = db.execute.call_args.args[0]
        self.assertIn("user-1", query.compile().params.values())

    def test_future_purchase_routes_to_goals(self):
        self.assertEqual(keyword_route("Planning to buy a car in 2 years"), "goal")
        self.assertEqual(keyword_route("create a goal planning to buy a car in 2 years"), "goal")
        self.assertEqual(keyword_route("Where should I buy a laptop?"), "purchase_optimize")
        self.assertEqual(keyword_route("Planning to buy a laptop today, which card should I use?"), "purchase_optimize")


if __name__ == "__main__":
    unittest.main()
