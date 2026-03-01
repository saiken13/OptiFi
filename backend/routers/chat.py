import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import groq

from database import get_db
from models.message import Message
from schemas.chat import ChatRequest, ChatResponse, ChatMessage
from agents.orchestrator import Orchestrator
from utils.security import get_current_user_id

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    user_msg = Message(
        user_id=user_id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    orchestrator = Orchestrator(db)
    try:
        result = await orchestrator.route(user_id=user_id, message=body.message, context=body.context)
    except groq.AuthenticationError:
        raise HTTPException(status_code=503, detail="AI service unavailable: invalid Groq API key. Check GROQ_API_KEY in .env.")
    except groq.APIError as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    assistant_msg = Message(
        user_id=user_id,
        role="assistant",
        content=result["response"],
        agent_type=result["intent"],
        structured_data=result.get("structured_data"),
    )
    db.add(assistant_msg)
    await db.flush()

    return ChatResponse(
        message=ChatMessage(
            id=assistant_msg.id,
            role="assistant",
            content=assistant_msg.content,
            agent_type=assistant_msg.agent_type,
            structured_data=assistant_msg.structured_data,
            created_at=assistant_msg.created_at,
        ),
        intent=result["intent"],
        processing_time_ms=result["processing_time_ms"],
    )


@router.get("/history", response_model=list[ChatMessage])
async def get_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    from sqlalchemy import select
    result = await db.execute(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return list(reversed(messages))
