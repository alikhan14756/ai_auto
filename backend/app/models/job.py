"""Persistent Automation Job queue model."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

# Standard Job Status Constants
JOB_STATUS_QUEUED = "QUEUED"
JOB_STATUS_PROCESSING = "PROCESSING"
JOB_STATUS_RETRYING = "RETRYING"
JOB_STATUS_COMPLETED = "COMPLETED"
JOB_STATUS_FAILED = "FAILED"
JOB_STATUS_CANCELLED = "CANCELLED"
JOB_STATUS_NEEDS_ATTENTION = "NEEDS_ATTENTION"

VALID_JOB_STATUSES = {
    JOB_STATUS_QUEUED,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_RETRYING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_CANCELLED,
    JOB_STATUS_NEEDS_ATTENTION,
}

# Allowed Transitions Map
ALLOWED_STATUS_TRANSITIONS = {
    JOB_STATUS_QUEUED: {JOB_STATUS_PROCESSING, JOB_STATUS_CANCELLED},
    JOB_STATUS_PROCESSING: {
        JOB_STATUS_COMPLETED,
        JOB_STATUS_RETRYING,
        JOB_STATUS_FAILED,
        JOB_STATUS_CANCELLED,
        JOB_STATUS_NEEDS_ATTENTION,
    },
    JOB_STATUS_RETRYING: {JOB_STATUS_QUEUED, JOB_STATUS_PROCESSING, JOB_STATUS_FAILED, JOB_STATUS_CANCELLED},
    JOB_STATUS_NEEDS_ATTENTION: {JOB_STATUS_QUEUED, JOB_STATUS_CANCELLED},
    JOB_STATUS_FAILED: {JOB_STATUS_QUEUED},  # Manual retry resets to QUEUED
    JOB_STATUS_COMPLETED: set(),  # Terminal state
    JOB_STATUS_CANCELLED: set(),  # Terminal state
}


class AutomationJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persistent database-backed asynchronous task queue record."""

    __tablename__ = "automation_jobs"

    channel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type = Column(String(64), nullable=False, index=True)  # TEST_DEMO, DISCOVER_TOPICS, SCRIPT, etc.
    payload = Column(JSON, nullable=False)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    status = Column(String(32), default=JOB_STATUS_QUEUED, nullable=False, index=True)
    priority = Column(Integer, default=10, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    locked_by = Column(String(128), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    progress_percentage = Column(Integer, default=0, nullable=False)
    current_stage = Column(String(64), nullable=True)
    error_log = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    channel = relationship("Channel", back_populates="automation_jobs")

    def can_transition_to(self, target_status: str) -> bool:
        """Check if transition from current status to target_status is permitted."""
        return target_status in ALLOWED_STATUS_TRANSITIONS.get(self.status, set())
