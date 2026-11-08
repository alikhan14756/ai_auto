"""Prompt template model."""

from sqlalchemy import Column, String, Text, JSON
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class PromptTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """System prompts and few-shot schemas with versioning."""

    __tablename__ = "prompt_templates"

    template_key = Column(String(64), unique=True, nullable=False, index=True)  # SCRIPT_LONG_FORM, FACT_CHECK, THUMBNAIL_HOOKS
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    schema_definition = Column(JSON, nullable=False)
    version = Column(String(16), default="v1.0.0", nullable=False)
