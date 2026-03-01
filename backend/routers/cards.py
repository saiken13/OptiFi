import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from database import get_db
from models.card import Card, CardRewardRule
from models.card_import_job import CardImportJob
from schemas.card import (
    CardCreate, CardResponse, CardImportSearchRequest,
    CardImportExtractRequest, CardImportConfirmRequest,
)
from utils.security import get_current_user_id
from services.card_import_service import CardImportService

router = APIRouter(prefix="/cards", tags=["cards"])


@router.post("", response_model=CardResponse)
async def create_card(
    body: CardCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    card = Card(**body.model_dump(), user_id=user_id)
    db.add(card)
    await db.flush()
    await db.refresh(card, ["reward_rules"])
    return card


@router.get("", response_model=list[CardResponse])
async def list_cards(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Card).options(selectinload(Card.reward_rules)).where(Card.user_id == user_id)
    )
    return result.scalars().all()


@router.delete("/{card_id}")
async def delete_card(
    card_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(select(Card).where(Card.id == card_id, Card.user_id == user_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    await db.delete(card)
    return {"ok": True}


# --- Card Import Pipeline ---

@router.post("/import/search")
async def import_search(
    body: CardImportSearchRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    job = CardImportJob(
        user_id=user_id,
        card_name=body.card_name,
        issuer=body.issuer,
        status="searching",
    )
    db.add(job)
    await db.flush()

    service = CardImportService()
    results = await service.search_card_pages(body.card_name, body.issuer)

    job.search_results = results
    job.status = "awaiting_url_selection"

    return {"job_id": str(job.id), "results": results}


@router.post("/import/extract")
async def import_extract(
    body: CardImportExtractRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    result = await db.execute(select(CardImportJob).where(CardImportJob.id == body.job_id, CardImportJob.user_id == user_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    job.status = "extracting"
    service = CardImportService()
    rules = await service.fetch_and_extract(job.card_name, job.issuer, body.selected_url)

    job.extracted_rules = rules
    job.status = "awaiting_confirmation"

    return {"job_id": str(job.id), "rules": rules}


@router.post("/import/confirm")
async def import_confirm(
    body: CardImportConfirmRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    card = Card(
        user_id=user_id,
        name=body.card_name,
        issuer=body.issuer,
    )
    db.add(card)
    await db.flush()

    for rule_data in body.rules:
        rule = CardRewardRule(card_id=card.id, **rule_data.model_dump())
        db.add(rule)

    result = await db.execute(select(CardImportJob).where(CardImportJob.id == body.job_id, CardImportJob.user_id == user_id))
    job = result.scalar_one_or_none()
    if job:
        job.status = "confirmed"

    await db.flush()
    await db.refresh(card, ["reward_rules"])
    return card
