import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Numeric, Boolean, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from database import Base


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Amazon Prime, Costco, Sam's Club, etc.
    merchant: Mapped[str] = mapped_column(String(255), nullable=False)  # amazon | costco | walmart
    annual_fee: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0)
    benefits: Mapped[Optional[dict]] = mapped_column(JSONB)  # {free_shipping: true, shipping_threshold: 0, discount_pct: 0}
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    renewal_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="memberships")
