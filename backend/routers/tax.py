from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from typing import Optional

from database import get_db
from models.user import User
from agents.tax_agent import TaxAgent
from utils.security import get_current_user_id
from utils.email import send_email, tax_report_html

router = APIRouter(prefix="/tax", tags=["tax"])


@router.get("/analysis")
async def get_tax_analysis(
    tax_year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    today = date.today()
    year = tax_year or (today.year - 1 if today.month < 4 else today.year)

    agent = TaxAgent(db)
    result = await agent.run(user_id=user_id, message="tax analysis", context={"tax_year": year})
    return result


@router.post("/email-report")
async def email_tax_report(
    tax_year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    today = date.today()
    year = tax_year or (today.year - 1 if today.month < 4 else today.year)

    agent = TaxAgent(db)
    result = await agent.run(user_id=user_id, message="tax analysis", context={"tax_year": year})

    user_q = await db.execute(select(User).where(User.id == user_id))
    user = user_q.scalar_one_or_none()
    sent = False
    if user and user.email:
        html = tax_report_html(result["response"], user.email, year)
        sent = await send_email(
            to_email=user.email,
            subject=f"Your {year} Tax Savings Report — OptiFi",
            html_body=html,
        )

    return {**result, "email_sent": sent}
