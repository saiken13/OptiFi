from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from database import get_db
from models.loan import Loan
from schemas.loan import LoanCreate, LoanUpdate, LoanResponse
from utils.security import get_current_user_id

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", response_model=LoanResponse)
async def create_loan(
    body: LoanCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    loan = Loan(**body.model_dump(), user_id=user_id)
    db.add(loan)
    await db.flush()
    return loan


@router.get("", response_model=list[LoanResponse])
async def list_loans(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(select(Loan).where(Loan.user_id == user_id))
    return result.scalars().all()


@router.patch("/{loan_id}", response_model=LoanResponse)
async def update_loan(
    loan_id: UUID,
    body: LoanUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(select(Loan).where(Loan.id == loan_id, Loan.user_id == user_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(loan, field, value)
    return loan


@router.delete("/{loan_id}")
async def delete_loan(
    loan_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(select(Loan).where(Loan.id == loan_id, Loan.user_id == user_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    await db.delete(loan)
    return {"ok": True}
