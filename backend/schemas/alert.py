from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class AlertResponse(BaseModel):
    id: UUID
    user_id: UUID
    alert_type: str
    title: str
    message: str
    is_read: bool
    metadata: Optional[dict] = Field(
        default=None,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )
    created_at: datetime

    model_config = {"from_attributes": True}


class MarkReadRequest(BaseModel):
    alert_ids: list[UUID]
