from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.weekly_review import WeeklyReview
from models.user import User
from agents.weekly_review_agent import WeeklyReviewAgent
from utils.security import get_current_user_id
from utils.helpers import get_week_bounds
from utils.email import send_email, weekly_review_html

router = APIRouter(prefix="/weekly-review", tags=["weekly-review"])


@router.post("/run")
async def run_weekly_review(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    agent = WeeklyReviewAgent(db)
    result = await agent.run(user_id=user_id, message="weekly review", context={})

    week_start, week_end = get_week_bounds()

    review = WeeklyReview(
        user_id=user_id,
        week_start=week_start,
        week_end=week_end,
        summary=result["response"],
        structured_data=result.get("structured_data"),
    )
    db.add(review)
    await db.flush()

    # Send email to user (best-effort — silently skipped if SMTP not configured)
    user_q = await db.execute(select(User).where(User.id == user_id))
    user = user_q.scalar_one_or_none()
    if user and user.email:
        html = weekly_review_html(result["response"], str(week_start), str(week_end))
        await send_email(
            to_email=user.email,
            subject=f"Your OptiFi Weekly Review — {week_start} to {week_end}",
            html_body=html,
        )

    return {
        "id": str(review.id),
        "week_start": str(week_start),
        "week_end": str(week_end),
        "summary": review.summary,
        "structured_data": review.structured_data,
    }


@router.get("/latest")
async def get_latest_review(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(WeeklyReview)
        .where(WeeklyReview.user_id == user_id)
        .order_by(WeeklyReview.created_at.desc())
        .limit(1)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="No weekly review found")
    return {
        "id": str(review.id),
        "week_start": str(review.week_start),
        "week_end": str(review.week_end),
        "summary": review.summary,
        "structured_data": review.structured_data,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }
