import re
from typing import Optional
from datetime import datetime, date, timedelta


CATEGORY_RULES: dict[str, list[str]] = {
    "dining": ["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "burger", "pizza", "sushi", "doordash", "ubereats", "grubhub", "chipotle"],
    "groceries": ["grocery", "supermarket", "whole foods", "trader joe", "kroger", "safeway", "publix", "aldi", "wegmans", "sprouts"],
    "gas": ["shell", "chevron", "bp", "exxon", "mobil", "gas station", "fuel", "speedway", "circle k"],
    "travel": ["airline", "hotel", "airbnb", "expedia", "booking.com", "uber", "lyft", "amtrak", "marriott", "hilton"],
    "shopping": ["amazon", "walmart", "target", "costco", "best buy", "apple store", "ebay", "etsy"],
    "entertainment": ["netflix", "spotify", "hulu", "disney+", "youtube", "cinema", "amc", "regal", "ticketmaster"],
    "health": ["pharmacy", "cvs", "walgreens", "hospital", "doctor", "dentist", "gym", "fitness"],
    "utilities": ["electric", "water", "internet", "comcast", "at&t", "verizon", "tmobile", "phone"],
    "subscriptions": ["subscription", "monthly", "annual plan", "membership"],
}


def categorize_transaction(description: str) -> Optional[str]:
    desc_lower = description.lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return None


def get_week_bounds(reference: Optional[date] = None) -> tuple[date, date]:
    ref = reference or date.today()
    week_start = ref - timedelta(days=ref.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def format_currency(amount: float) -> str:
    return f"${amount:,.2f}"


def calculate_months_to_goal(target: float, current: float, monthly: float) -> Optional[float]:
    if monthly <= 0:
        return None
    remaining = target - current
    if remaining <= 0:
        return 0
    return remaining / monthly


def loan_amortization(balance: float, annual_rate: float, monthly_payment: float, extra: float = 0.0) -> list[dict]:
    monthly_rate = annual_rate / 100 / 12
    schedule = []
    month = 0
    current_balance = balance

    while current_balance > 0 and month < 600:
        month += 1
        interest = current_balance * monthly_rate
        payment = min(monthly_payment + extra, current_balance + interest)
        principal = payment - interest
        current_balance = max(0, current_balance - principal)
        schedule.append({
            "month": month,
            "payment": round(payment, 2),
            "principal": round(principal, 2),
            "interest": round(interest, 2),
            "balance": round(current_balance, 2),
        })

    return schedule


def clean_html_for_llm(html: str, max_chars: int = 12000) -> str:
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]
