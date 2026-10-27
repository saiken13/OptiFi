import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agents.orchestrator import Orchestrator, keyword_route
from agents.purchase_agent import PurchaseAgent
from services.purchase_optimizer import PurchaseOptimizerService


class PurchaseClarificationTests(unittest.IsolatedAsyncioTestCase):
    def agent(self, **fields):
        agent = object.__new__(PurchaseAgent)
        agent.db = MagicMock()
        agent.db.execute = AsyncMock(return_value=MagicMock())
        agent.db.execute.return_value.scalars.return_value.all.return_value = []
        agent.ask_llm = AsyncMock(return_value=json.dumps({"action": "search", "query": "bike", **fields}))
        agent.format_response = AsyncMock(return_value="Results")
        return agent

    async def test_missing_budget_and_bike_type_do_not_search(self):
        agent = self.agent()
        with patch("agents.purchase_agent.PurchaseOptimizerService") as service:
            result = await agent.run("user-1", "Where should I buy a bike?", {})
            service.assert_not_called()
        self.assertIn("maximum purchase budget", result["response"])
        self.assertIn("bicycle or a motorcycle", result["response"])
        self.assertEqual(result["structured_data"]["purchase_action"], "needs_details")
        agent.db.execute.assert_not_awaited()

    async def test_known_budget_does_not_resolve_ambiguous_bike(self):
        agent = self.agent(budget=500)
        result = await agent.run("user-1", "Find a bike for $500", {})
        self.assertIn("bicycle or a motorcycle", result["response"])
        agent.db.execute.assert_not_awaited()

    async def test_followup_preserves_product_and_supplies_budget(self):
        agent = self.agent(query="bicycle", budget=500)
        pending = {"query": "bike", "budget": None, "action": "search"}
        with patch("agents.purchase_agent.PurchaseOptimizerService") as service:
            service.return_value.optimize = AsyncMock(return_value={"best_option": {"price": 400}})
            await agent.run("user-1", "Bicycle, my budget is $500", {"pending_purchase": pending})
            service.return_value.optimize.assert_awaited_once_with(query="bicycle", cards=[], memberships=[], budget=500)
        supplied = json.loads(agent.ask_llm.call_args.kwargs["user"])
        self.assertEqual(supplied["pending_purchase"], pending)

    async def test_no_results_cannot_generate_a_recommendation(self):
        agent = self.agent(query="bicycle", budget=500)
        with patch("agents.purchase_agent.PurchaseOptimizerService") as service:
            service.return_value.optimize = AsyncMock(return_value={"best_option": None, "data_status": "sample_only"})
            result = await agent.run("user-1", "Bicycle under $500", {})
        self.assertIn("couldn't retrieve real", result["response"])
        agent.format_response.assert_not_awaited()

    async def test_budget_reply_resumes_pending_shopping_instead_of_creating_budget(self):
        agent = self.agent()
        pending = {"query": "bicycle", "budget": None}
        agent.db.execute.return_value.scalar_one_or_none.return_value = SimpleNamespace(
            structured_data={"pending_purchase": pending})
        orchestrator = object.__new__(Orchestrator)
        orchestrator.db = agent.db
        purchase = SimpleNamespace(run=AsyncMock(return_value={"response": "Question", "structured_data": {}}))
        orchestrator.agents = {"purchase_optimize": purchase, "general": None}
        await orchestrator.route("user-1", "My budget is $500", {"pending_purchase": {"query": "untrusted"}})
        self.assertEqual(purchase.run.call_args.kwargs["context"]["pending_purchase"], pending)

    async def test_optimizer_filters_upfront_cost_before_rewards(self):
        service = PurchaseOptimizerService()
        service._enhance_query = AsyncMock(return_value="bicycle")
        service._search_products = AsyncMock(return_value=[
            {"merchant": "A", "price": 490, "shipping": 20, "url": "https://example.com/a"},
            {"merchant": "B", "price": 450, "shipping": 10, "url": "https://example.com/b"},
        ])
        result = await service.optimize("bicycle", [], [], budget=500)
        self.assertEqual(len(result["all_options"]), 1)
        self.assertEqual(result["best_option"]["merchant"], "B")

    async def test_sample_products_are_not_ranked_as_real_listings(self):
        service = PurchaseOptimizerService()
        service._enhance_query = AsyncMock(return_value="bicycle")
        service._search_products = AsyncMock(return_value=service._mock_products("bicycle"))
        result = await service.optimize("bicycle", [], [], budget=500)
        self.assertIsNone(result["best_option"])
        self.assertEqual(result["all_options"], [])
        self.assertEqual(result["data_status"], "sample_only")

    def test_planning_without_deadline_starts_goal_flow(self):
        self.assertEqual(keyword_route("I am planning to buy a bike"), "goal")
        self.assertEqual(keyword_route("Planning to buy a laptop today, which card should I use?"), "purchase_optimize")
        self.assertEqual(keyword_route("Where should I buy a bicycle with a budget of $500?"), "purchase_optimize")


if __name__ == "__main__":
    unittest.main()
