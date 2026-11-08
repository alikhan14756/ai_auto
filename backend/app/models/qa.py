"""Autonomous Quality Assurance and Veto Gate models."""

from sqlalchemy import Column, Integer, Boolean, ForeignKey, Numeric, JSON, String, Text, DateTime
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class QualityReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Deterministic 14-point pre-publish audit verification result (Legacy/Render QA)."""

    __tablename__ = "quality_reports"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    render_job_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("render_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    all_checks_passed = Column(Boolean, nullable=False)
    black_frame_duration_max = Column(Numeric(6, 3), nullable=False)
    freeze_duration_max = Column(Numeric(6, 3), nullable=False)
    integrated_loudness_lufs = Column(Numeric(4, 2), nullable=False)
    max_true_peak_dbtp = Column(Numeric(4, 2), nullable=False)
    unverified_claims_count = Column(Integer, nullable=False)
    transcript_similarity_ratio = Column(Numeric(4, 3), nullable=False)
    diagnostic_details = Column(JSON, nullable=False)

    # Relationships
    project = relationship("VideoProject", back_populates="quality_reports")
    render_job = relationship("RenderJob", back_populates="quality_reports")


class QARun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Comprehensive multi-category QA evaluation execution run."""

    __tablename__ = "qa_runs"

    project_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    publication_package_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("publication_packages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    run_number = Column(Integer, default=1, nullable=False)
    status = Column(String(32), default="QUEUED", nullable=False, index=True)  # QUEUED, RUNNING, COMPLETED, FAILED
    overall_score = Column(Numeric(5, 2), nullable=True)
    veto_decision = Column(String(32), default="BLOCKED", nullable=False, index=True)  # BLOCKED, NEEDS_REVIEW, READY_FOR_APPROVAL, APPROVED
    can_publish = Column(Boolean, default=False, nullable=False)
    input_versions_snapshot = Column(JSON, default=dict, nullable=False)
    summary = Column(JSON, default=dict, nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    project = relationship("VideoProject", back_populates="qa_runs")
    publication_package = relationship("PublicationPackage", back_populates="qa_runs")
    checks = relationship("QACheck", back_populates="qa_run", cascade="all, delete-orphan", order_by="QACheck.created_at", lazy="selectin")
    findings = relationship("QAFinding", back_populates="qa_run", cascade="all, delete-orphan", order_by="QAFinding.created_at", lazy="selectin")
    category_scores = relationship("QACategoryScore", back_populates="qa_run", cascade="all, delete-orphan", order_by="QACategoryScore.category", lazy="selectin")


class QACheck(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual validator check result within a QA run."""

    __tablename__ = "qa_checks"

    qa_run_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("qa_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = Column(String(64), nullable=False, index=True)
    check_name = Column(String(128), nullable=False, index=True)
    status = Column(String(32), default="PASSED", nullable=False)  # PASSED, WARNING, FAILED, SKIPPED
    score = Column(Numeric(5, 2), default=100.0, nullable=False)
    execution_time_ms = Column(Integer, default=0, nullable=False)
    metrics = Column(JSON, default=dict, nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    qa_run = relationship("QARun", back_populates="checks")
    findings = relationship("QAFinding", back_populates="check", cascade="all, delete-orphan")


class QAFinding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Specific defect, compliance failure, or optimization alert discovered by a check."""

    __tablename__ = "qa_findings"

    qa_run_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("qa_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    check_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("qa_checks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(32), default="OPEN", nullable=False, index=True)  # OPEN, IN_PROGRESS, RESOLVED, ACCEPTED_WITH_EXCEPTION, NEEDS_REVIEW
    affected_artifact = Column(String(128), nullable=False)
    title = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=False)
    evidence = Column(JSON, default=dict, nullable=False)
    recommended_correction = Column(Text, nullable=False)
    requires_human_review = Column(Boolean, default=False, nullable=False)
    resolved_by_user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Relationships
    qa_run = relationship("QARun", back_populates="findings")
    check = relationship("QACheck", back_populates="findings")
    exceptions = relationship("QAException", back_populates="finding", cascade="all, delete-orphan", lazy="selectin")
    resolved_by = relationship("User", back_populates="qa_resolved_findings")


class QACategoryScore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Aggregated score and metrics for a specific QA category in a run."""

    __tablename__ = "qa_category_scores"

    qa_run_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("qa_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = Column(String(64), nullable=False, index=True)
    weight = Column(Numeric(4, 2), nullable=False)  # 0.00 to 1.00
    raw_score = Column(Numeric(5, 2), nullable=False)  # 0.00 to 100.00
    weighted_score = Column(Numeric(5, 2), nullable=False)
    deductions = Column(JSON, default=list, nullable=False)
    check_count = Column(Integer, default=0, nullable=False)
    passed_count = Column(Integer, default=0, nullable=False)
    warning_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)

    # Relationships
    qa_run = relationship("QARun", back_populates="category_scores")


class QAException(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Authorized administrative override for HIGH severity findings."""

    __tablename__ = "qa_exceptions"

    finding_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("qa_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    authorized_by_user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    finding = relationship("QAFinding", back_populates="exceptions")
    authorized_by = relationship("User", back_populates="qa_exceptions")
