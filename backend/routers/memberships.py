from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from database import get_db
from models.membership import Membership
from schemas.membership import MembershipCreate, MembershipResponse
from utils.security import get_current_user_id

router = APIRouter(prefix="/memberships", tags=["memberships"])


@router.post("", response_model=MembershipResponse)
async def create_membership(
    body: MembershipCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    membership = Membership(**body.model_dump(), user_id=user_id)
    db.add(membership)
    await db.flush()
    return membership


@router.get("", response_model=list[MembershipResponse])
async def list_memberships(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(select(Membership).where(Membership.user_id == user_id))
    return result.scalars().all()


@router.delete("/{membership_id}")
async def delete_membership(
    membership_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Membership).where(Membership.id == membership_id, Membership.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    await db.delete(membership)
    return {"ok": True}
