from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from datetime import date

from database import get_db
from models.transaction import Transaction
from models.budget import Budget
from schemas.transaction import TransactionCreate, TransactionResponse, TransactionSummary
from utils.security import get_current_user_id
from services.transaction_service import parse_csv, process_transactions

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse)
async def create_transaction(
    body: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    txn = Transaction(
        user_id=user_id,
        date=body.date,
        description=body.description,
        amount=body.amount,
        category=body.category,
        merchant=body.merchant,
    )
    db.add(txn)

    # If expense, deduct from matching budget for current month
    if body.amount < 0 and body.category:
        today = date.today()
        budget_q = await db.execute(
            select(Budget).where(
                and_(
                    Budget.user_id == user_id,
                    Budget.category == body.category,
                    Budget.month == today.month,
                    Budget.year == today.year,
                )
            )
        )
        budget = budget_q.scalar_one_or_none()
        if budget:
            budget.spent_this_month = float(budget.spent_this_month) + abs(body.amount)
            db.add(budget)

    await db.flush()
    return txn


@router.post("/upload", response_model=dict)
async def upload_transactions(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = await file.read()
    try:
        raw_records = parse_csv(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    processed = await process_transactions(raw_records)

    saved_count = 0
    for r in processed:
        txn = Transaction(
            user_id=user_id,
            date=r["date"],
            description=r["description"],
            amount=r["amount"],
            category=r.get("category"),
            account=r.get("account"),
        )
        db.add(txn)
        saved_count += 1

    return {"imported": saved_count}


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    month: Optional[int] = None,
    year: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    query = select(Transaction).where(Transaction.user_id == user_id)
    if month:
        query = query.where(extract("month", Transaction.date) == month)
    if year:
        query = query.where(extract("year", Transaction.date) == year)
    if category:
        query = query.where(Transaction.category == category)
    query = query.order_by(Transaction.date.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/summary", response_model=TransactionSummary)
async def get_summary(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    today = date.today()
    m = month or today.month
    y = year or today.year

    result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.user_id == user_id,
                extract("month", Transaction.date) == m,
                extract("year", Transaction.date) == y,
            )
        )
    )
    transactions = result.scalars().all()

    total_income = sum(float(t.amount) for t in transactions if float(t.amount) > 0)
    total_expenses = sum(abs(float(t.amount)) for t in transactions if float(t.amount) < 0)

    by_category: dict[str, float] = {}
    merchant_counts: dict[str, float] = {}
    for t in transactions:
        if float(t.amount) < 0:
            cat = t.category or "uncategorized"
            by_category[cat] = by_category.get(cat, 0) + abs(float(t.amount))
            if t.merchant:
                merchant_counts[t.merchant] = merchant_counts.get(t.merchant, 0) + abs(float(t.amount))

    top_merchants = sorted(
        [{"merchant": k, "amount": round(v, 2)} for k, v in merchant_counts.items()],
        key=lambda x: x["amount"],
        reverse=True,
    )[:5]

    period_start = date(y, m, 1)
    import calendar
    last_day = calendar.monthrange(y, m)[1]
    period_end = date(y, m, last_day)

    return TransactionSummary(
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        net=round(total_income - total_expenses, 2),
        by_category={k: round(v, 2) for k, v in by_category.items()},
        top_merchants=top_merchants,
        period_start=period_start,
        period_end=period_end,
    )
