"""AI and API provider usage metering model."""

from sqlalchemy import Column, String, Integer, ForeignKey, Numeric, DateTime, func
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin


class ProviderUsage(Base, UUIDPrimaryKeyMixin):
    """Token usage and cost accounting ledger per channel."""

    __tablename__ = "provider_usages"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_name = Column(String(64), nullable=False, index=True)  # GEMINI_FLASH, GEMINI_PRO, SEARCH_API
    model_name = Column(String(128), nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    cost_usd = Column(Numeric(8, 6), default=0.000000, nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False, index=True)

    # Relationships
    channel = relationship("Channel", back_populates="provider_usages")
