import httpx
import re
from typing import Optional
from urllib.parse import urlparse
import groq
from database import settings

_VEHICLE_KEYWORDS = [
    "honda", "toyota", "ford", "chevrolet", "chevy", "bmw", "mercedes", "audi",
    "volkswagen", "hyundai", "kia", "nissan", "mazda", "subaru", "jeep", "dodge",
    "ram", "gmc", "cadillac", "lexus", "acura", "infiniti", "volvo", "porsche",
    "tesla", "ferrari", "lamborghini", "bentley", "mclaren", "accord", "civic",
    "camry", "corolla", "mustang", "silverado", "f-150", "f150", "model 3",
    "model s", "model x", "model y", "prius", "highlander", "rav4", "cr-v",
    "pilot", "tahoe", "suburban", "explorer", "escape", "altima", "sentra",
    "outback", "wrangler", "charger", "challenger", "used car", "new car",
    " car ", "truck", " suv", "sedan", "coupe", "hatchback", "convertible",
    "minivan", "vehicle", "automobile",
]


class PurchaseOptimizerService:

    async def _enhance_query(self, query: str) -> str:
        """Use LLM to make the query specific enough to return real physical products."""
        try:
            client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)
            response = await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                max_tokens=60,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Rewrite this shopping query to be specific and find real physical products "
                        f"(not toys, miniatures, or accessories). Return only the improved search query, nothing else: {query}"
                    ),
                }],
            )
            enhanced = response.choices[0].message.content.strip().strip('"').strip("'")
            return enhanced if enhanced else query
        except Exception:
            return query

    def _is_vehicle_query(self, query: str) -> bool:
        q_lower = f" {query.lower()} "
        return any(kw in q_lower for kw in _VEHICLE_KEYWORDS)

    async def _search_vehicles(self, query: str) -> list[dict]:
        """Use web search for vehicles since Google Shopping doesn't list cars."""
        if not settings.SERPER_API_KEY:
            return self._mock_products(query)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": settings.SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": f"{query} for sale price site:cargurus.com OR site:autotrader.com OR site:cars.com OR site:carmax.com OR site:edmunds.com", "num": 10},
            )
            if response.status_code == 200:
                data = response.json()
                products = []
                for item in data.get("organic", [])[:8]:
                    url = item.get("link", "#")
                    title = item.get("title", query)
                    snippet = item.get("snippet", "")
                    # Extract first $ price from snippet or title
                    price_match = re.search(r'\$\s*([\d,]+)', snippet + " " + title)
                    price = 0.0
                    if price_match:
                        try:
                            price = float(price_match.group(1).replace(",", ""))
                        except ValueError:
                            pass
                    if price < 500:
                        # Skip implausibly low prices (likely not vehicle prices)
                        continue
                    domain = urlparse(url).netloc.replace("www.", "")
                    products.append({
                        "merchant": domain,
                        "title": title,
                        "price": price,
                        "shipping": 0.0,
                        "url": url,
                        "in_stock": True,
                    })
                if products:
                    return products
        return self._mock_products(query)

    async def _search_products(self, query: str) -> list[dict]:
        if self._is_vehicle_query(query):
            return await self._search_vehicles(query)

        if not settings.SERPER_API_KEY:
            return self._mock_products(query)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://google.serper.dev/shopping",
                headers={"X-API-KEY": settings.SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": 10},
            )
            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        "merchant": item.get("source", "Unknown"),
                        "title": item.get("title", query),
                        "price": float(item.get("price", "0").replace("$", "").replace(",", "") or 0),
                        "shipping": 0.0,
                        "url": item.get("link", "#"),
                        "in_stock": True,
                    }
                    for item in data.get("shopping", [])[:8]
                    if item.get("price")
                ]
        return self._mock_products(query)

    def _mock_products(self, query: str) -> list[dict]:
        base = 49.99
        return [
            {"merchant": "Amazon", "title": query, "price": base, "shipping": 0.0, "url": "https://amazon.com", "in_stock": True},
            {"merchant": "Walmart", "title": query, "price": base * 0.97, "shipping": 5.99, "url": "https://walmart.com", "in_stock": True},
            {"merchant": "Target", "title": query, "price": base * 1.02, "shipping": 5.99, "url": "https://target.com", "in_stock": True},
            {"merchant": "Best Buy", "title": query, "price": base * 1.05, "shipping": 0.0, "url": "https://bestbuy.com", "in_stock": True},
        ]

    def _apply_membership(self, merchant: str, price: float, shipping: float, memberships: list) -> tuple[float, float, Optional[str]]:
        merchant_lower = merchant.lower()
        for m in memberships:
            m_merchant = m.merchant.lower()
            if m_merchant in merchant_lower or merchant_lower in m_merchant:
                benefits = m.benefits or {}
                new_shipping = 0.0 if benefits.get("free_shipping") else shipping
                discount_pct = benefits.get("discount_pct", 0)
                discounted_price = price * (1 - discount_pct / 100) if discount_pct else price
                return discounted_price, new_shipping, m.name
        return price, shipping, None

    def _best_card_rate(self, merchant: str, cards: list) -> tuple[float, Optional[str], Optional[str], Optional[str]]:
        best_rate = 0.0
        best_card_id = None
        best_card_name = None
        best_evidence = None

        merchant_lower = merchant.lower()
        for card in cards:
            for rule in card.reward_rules:
                matches = (
                    rule.category == "all"
                    or rule.category.lower() in merchant_lower
                    or (rule.merchant_match and rule.merchant_match.lower() in merchant_lower)
                    or merchant_lower in rule.category.lower()
                )
                if matches and float(rule.reward_rate) > best_rate:
                    best_rate = float(rule.reward_rate)
                    best_card_id = str(card.id)
                    best_card_name = f"{card.name} ({card.issuer})"
                    best_evidence = rule.evidence

        # Fallback: if no specific match, use the best "all" category rule across all cards
        if best_rate == 0.0:
            for card in cards:
                for rule in card.reward_rules:
                    if rule.category == "all" and float(rule.reward_rate) > best_rate:
                        best_rate = float(rule.reward_rate)
                        best_card_id = str(card.id)
                        best_card_name = f"{card.name} ({card.issuer})"
                        best_evidence = rule.evidence

        return best_rate, best_card_id, best_card_name, best_evidence

    def _all_card_rates(self, merchant: str, effective_price: float, cards: list) -> list[dict]:
        """Return every card's best rate for this merchant, sorted by cashback descending."""
        merchant_lower = merchant.lower()
        results = []
        for card in cards:
            card_best_rate = 0.0
            card_evidence = None
            for rule in card.reward_rules:
                matches = (
                    rule.category == "all"
                    or rule.category.lower() in merchant_lower
                    or (rule.merchant_match and rule.merchant_match.lower() in merchant_lower)
                    or merchant_lower in rule.category.lower()
                )
                if matches and float(rule.reward_rate) > card_best_rate:
                    card_best_rate = float(rule.reward_rate)
                    card_evidence = rule.evidence
            results.append({
                "card_name": f"{card.name} ({card.issuer})",
                "card_id": str(card.id),
                "cashback_rate": round(card_best_rate, 4),
                "cashback_amount": round(effective_price * card_best_rate, 2),
                "evidence": card_evidence,
            })
        return sorted(results, key=lambda x: x["cashback_amount"], reverse=True)

    async def optimize(self, query: str, cards: list, memberships: list) -> dict:
        enhanced_query = await self._enhance_query(query)
        products = await self._search_products(enhanced_query)

        options = []
        for p in products:
            price = p["price"]
            shipping = p["shipping"]
            merchant = p["merchant"]

            eff_price, eff_shipping, membership_name = self._apply_membership(
                merchant, price, shipping, memberships
            )
            membership_savings = (price + shipping) - (eff_price + eff_shipping)

            rate, card_id, card_name, evidence = self._best_card_rate(merchant, cards)
            effective_total = eff_price + eff_shipping
            cashback = round(effective_total * rate, 2)
            net_cost = round(effective_total - cashback, 2)

            card_options = self._all_card_rates(merchant, effective_total, cards)

            options.append({
                "merchant": merchant,
                "price": price,
                "shipping": shipping,
                "shipping_after_membership": eff_shipping,
                "membership_savings": round(membership_savings, 2),
                "membership_name": membership_name,
                "best_card_id": card_id,
                "best_card_name": card_name,
                "cashback_rate": rate,
                "cashback_amount": cashback,
                "net_cost": net_cost,
                "total_savings": round((price + shipping) - net_cost, 2),
                "url": p["url"],
                "evidence": evidence,
                "card_options": card_options,
            })

        options.sort(key=lambda x: x["net_cost"])
        ranked = [{"rank": i + 1, **o} for i, o in enumerate(options)]

        return {
            "query": query,
            "enhanced_query": enhanced_query,
            "best_option": ranked[0] if ranked else None,
            "alternatives": ranked[1:4],
            "all_options": ranked,
        }
