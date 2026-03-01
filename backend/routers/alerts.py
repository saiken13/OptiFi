from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from database import get_db
from models.alert import Alert
from schemas.alert import AlertResponse, MarkReadRequest
from utils.security import get_current_user_id

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    query = select(Alert).where(Alert.user_id == user_id).order_by(Alert.created_at.desc()).limit(50)
    if unread_only:
        query = query.where(Alert.is_read == False)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/mark-read")
async def mark_read(
    body: MarkReadRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    await db.execute(
        update(Alert)
        .where(Alert.id.in_(body.alert_ids), Alert.user_id == user_id)
        .values(is_read=True)
    )
    return {"ok": True}
