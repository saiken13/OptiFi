from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
from datetime import date

from database import get_db
from models.budget import Budget
from schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from utils.security import get_current_user_id

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetResponse)
async def create_budget(
    body: BudgetCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    budget = Budget(**body.model_dump(), user_id=user_id)
    db.add(budget)
    await db.flush()
    return budget


@router.get("", response_model=list[BudgetResponse])
async def list_budgets(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    today = date.today()
    m = month or today.month
    y = year or today.year
    result = await db.execute(
        select(Budget).where(and_(Budget.user_id == user_id, Budget.month == m, Budget.year == y))
    )
    return result.scalars().all()


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: UUID,
    body: BudgetUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(budget, field, value)
    return budget


@router.delete("/{budget_id}")
async def delete_budget(
    budget_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    await db.delete(budget)
    return {"ok": True}
