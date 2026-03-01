from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None  # optional context (current page, selected goal id, etc.)


class ChatMessage(BaseModel):
    id: UUID
    role: str
    content: str
    agent_type: Optional[str]
    structured_data: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    message: ChatMessage
    intent: str
    processing_time_ms: int
