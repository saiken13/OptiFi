import json
from typing import Optional
from pathlib import Path
import httpx
import groq
from database import settings
from utils.helpers import clean_html_for_llm

_extract_prompt: Optional[str] = None


def _load_extract_prompt() -> str:
    global _extract_prompt
    if _extract_prompt is None:
        path = Path(__file__).parent.parent / "prompts" / "card_extract.txt"
        _extract_prompt = path.read_text()
    return _extract_prompt


class CardImportService:
    def __init__(self):
        self.client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def search_card_pages(self, card_name: str, issuer: str) -> list[dict]:
        if not settings.SERPER_API_KEY:
            return self._mock_search_results(card_name, issuer)

        query = f"{issuer} {card_name} credit card rewards benefits site:{issuer.lower().replace(' ', '')}.com OR {issuer.lower().replace(' ', '')}creditcard"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": settings.SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": f"{issuer} {card_name} credit card rewards categories cashback", "num": 5},
            )
            if response.status_code == 200:
                data = response.json()
                return [
                    {"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")}
                    for r in data.get("organic", [])[:5]
                ]
        return self._mock_search_results(card_name, issuer)

    def _mock_search_results(self, card_name: str, issuer: str) -> list[dict]:
        return [
            {
                "title": f"{issuer} {card_name} Rewards & Benefits",
                "url": f"https://www.{issuer.lower().replace(' ', '')}.com/credit-cards/{card_name.lower().replace(' ', '-')}/rewards",
                "snippet": f"Earn rewards with your {card_name}. Get cashback on dining, travel, groceries and more.",
            }
        ]

    async def fetch_and_extract(self, card_name: str, issuer: str, url: str) -> list[dict]:
        page_content = await self._fetch_page(url)
        if not page_content:
            return []
        return await self._extract_rules(card_name, issuer, url, page_content)

    async def _fetch_page(self, url: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; OptiFi/1.0; +https://optifi.app)"},
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return clean_html_for_llm(response.text)
        except Exception:
            pass
        return None

    async def _extract_rules(self, card_name: str, issuer: str, source_url: str, page_content: str) -> list[dict]:
        prompt = _load_extract_prompt()
        prompt = (
            prompt.replace("{card_name}", card_name)
            .replace("{issuer}", issuer)
            .replace("{source_url}", source_url)
            .replace("{page_content}", page_content)
        )

        response = await self.client.chat.completions.create(
            model=settings.GROQ_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        try:
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            rules = json.loads(raw)
            return rules if isinstance(rules, list) else []
        except json.JSONDecodeError:
            return []
