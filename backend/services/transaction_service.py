import io
import json
from typing import Optional
from pathlib import Path
from datetime import date
import pandas as pd
import groq
from database import settings
from utils.helpers import categorize_transaction

_categorize_prompt: Optional[str] = None


def _load_categorize_prompt() -> str:
    global _categorize_prompt
    if _categorize_prompt is None:
        path = Path(__file__).parent.parent / "prompts" / "transaction_categorize.txt"
        _categorize_prompt = path.read_text()
    return _categorize_prompt


COLUMN_ALIASES = {
    "date": ["date", "transaction date", "trans date", "posted date"],
    "description": ["description", "name", "merchant", "payee", "details", "memo"],
    "amount": ["amount", "debit", "credit", "transaction amount"],
    "account": ["account", "account name", "account number"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.lower().strip() for c in df.columns]
    rename_map = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for col in df.columns:
            if col in aliases and canonical not in df.columns:
                rename_map[col] = canonical
                break
    return df.rename(columns=rename_map)


def parse_csv(content: bytes) -> list[dict]:
    df = pd.read_csv(io.BytesIO(content))
    df = _normalize_columns(df)

    required = {"date", "description", "amount"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["amount"] = pd.to_numeric(df["amount"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
    df = df.dropna(subset=["date", "amount"])

    records = []
    for _, row in df.iterrows():
        records.append({
            "date": row["date"],
            "description": str(row.get("description", "")),
            "amount": float(row["amount"]),
            "account": str(row.get("account", "")) if "account" in df.columns else None,
        })
    return records


async def categorize_with_llm(uncategorized: list[str]) -> dict[str, str]:
    if not uncategorized or not settings.GROQ_API_KEY:
        return {}

    client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)
    prompt = _load_categorize_prompt().replace("{transactions}", json.dumps(uncategorized))

    try:
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return {}


async def process_transactions(raw_records: list[dict]) -> list[dict]:
    uncategorized_descs = []
    for r in raw_records:
        cat = categorize_transaction(r["description"])
        r["category"] = cat
        if cat is None:
            uncategorized_descs.append(r["description"])

    if uncategorized_descs:
        llm_categories = await categorize_with_llm(list(set(uncategorized_descs)))
        for r in raw_records:
            if r["category"] is None:
                r["category"] = llm_categories.get(r["description"], "other")

    return raw_records
