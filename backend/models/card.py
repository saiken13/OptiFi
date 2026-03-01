import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from database import Base


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    last_four: Mapped[Optional[str]] = mapped_column(String(4))
    network: Mapped[Optional[str]] = mapped_column(String(50))  # visa | mastercard | amex | discover
    annual_fee: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="cards")
    reward_rules: Mapped[list["CardRewardRule"]] = relationship("CardRewardRule", back_populates="card", cascade="all, delete-orphan")


class CardRewardRule(Base):
    __tablename__ = "card_reward_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # cashback | points | miles
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # dining | travel | groceries | gas | all | merchant_name
    reward_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)  # e.g. 0.03 = 3%
    cap_amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))  # spending cap for this rate
    cap_period: Mapped[Optional[str]] = mapped_column(String(20))  # monthly | quarterly | annual
    merchant_match: Mapped[Optional[str]] = mapped_column(String(255))  # specific merchant name if applicable
    activation_required: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence: Mapped[Optional[str]] = mapped_column(String(1000))  # exact text from card page
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    card: Mapped["Card"] = relationship("Card", back_populates="reward_rules")
