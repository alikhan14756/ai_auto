"""User and Authentication models."""

from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account mapped to Supabase Auth."""

    __tablename__ = "users"

    supabase_user_id = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    role = Column(String(32), default="CREATOR", nullable=False)  # SUPER_ADMIN, ADMIN, CREATOR

    # Relationships
    channels = relationship("Channel", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    qa_resolved_findings = relationship("QAFinding", back_populates="resolved_by")
    qa_exceptions = relationship("QAException", back_populates="authorized_by")
