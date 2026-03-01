from .base_agent import BaseAgent

SYSTEM_PROMPT = """You are OptiFi, an expert personal finance AI assistant.
You help users with budgeting, saving goals, debt payoff, investment basics, and general money management.
Be concise, specific, and actionable. Use the user's actual financial data when available.
Always structure responses clearly with headers when appropriate.
If asked about specific financial products, remind users to verify details independently."""


class GeneralAgent(BaseAgent):
    async def run(self, user_id: str, message: str, context: dict) -> dict:
        await self._extract_and_save_financial_data(user_id, message)

        response = await self.ask_llm(
            system=SYSTEM_PROMPT,
            user=message,
            max_tokens=1000,
        )
        return {"response": response, "structured_data": None}
