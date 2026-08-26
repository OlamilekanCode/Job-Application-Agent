from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class CandidateProfile(TimestampMixin, Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("profile"))
    full_name: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    location: Mapped[str] = mapped_column(String(255), default="Nigeria")
    headline: Mapped[str] = mapped_column(String(255), default="")
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    facts: Mapped[list["CandidateFact"]] = relationship(back_populates="profile")


class CandidateFact(TimestampMixin, Base):
    __tablename__ = "candidate_facts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("fact"))
    profile_id: Mapped[str] = mapped_column(ForeignKey("candidate_profiles.id"))
    category: Mapped[str] = mapped_column(String(80))
    field_name: Mapped[str] = mapped_column(String(120))
    structured_value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    human_value: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(120))
    confirmation_state: Mapped[str] = mapped_column(String(40), default="proposed")
    sensitivity: Mapped[str] = mapped_column(String(40), default="normal")
    valid_contexts: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edit_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    profile: Mapped[CandidateProfile] = relationship(back_populates="facts")


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("job"))
    source: Mapped[str] = mapped_column(String(80))
    source_identifier: Mapped[str] = mapped_column(String(255))
    canonical_url: Mapped[str] = mapped_column(String(1024))
    company: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(255), default="")
    remote_policy: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(40), default="discovered")
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    __table_args__ = (UniqueConstraint("source", "source_identifier", name="uq_jobs_source_id"),)


class JobSnapshot(TimestampMixin, Base):
    __tablename__ = "job_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("snapshot"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    snapshot_type: Mapped[str] = mapped_column(String(80), default="description")
    content_hash: Mapped[str] = mapped_column(String(128))
    content_text: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class JobEvidence(TimestampMixin, Base):
    __tablename__ = "job_evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("evidence"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    category: Mapped[str] = mapped_column(String(80))
    evidence_text: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(1024))
    confidence: Mapped[str] = mapped_column(String(40), default="medium")


class JobScore(TimestampMixin, Base):
    __tablename__ = "job_scores"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("score"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    total_score: Mapped[int] = mapped_column(Integer)
    components: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    penalties: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(120), default="phase1-static")


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("app"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    state: Mapped[str] = mapped_column(String(80), default="discovered")
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApplicationEvent(TimestampMixin, Base):
    __tablename__ = "application_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("appevt"))
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"))
    actor: Mapped[str] = mapped_column(String(80), default="system")
    event_type: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("conv"))
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    application_id: Mapped[str | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), default="")


class ConversationMessage(TimestampMixin, Base):
    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("msg"))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(40))
    content: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class AIRun(TimestampMixin, Base):
    __tablename__ = "ai_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("airun"))
    provider: Mapped[str] = mapped_column(String(80), default="codex")
    codex_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_name: Mapped[str] = mapped_column(String(120))
    prompt_version: Mapped[str] = mapped_column(String(80))
    schema_version: Mapped[str] = mapped_column(String(80))
    model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    input_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    validation_state: Mapped[str] = mapped_column(String(40), default="pending")
    usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("doc"))
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("candidate_profiles.id"), nullable=True)
    document_type: Mapped[str] = mapped_column(String(80), default="original_cv")
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    storage_path: Mapped[str] = mapped_column(String(1024), default="")
    content_hash: Mapped[str] = mapped_column(String(128), default="")
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class BrowserSession(TimestampMixin, Base):
    __tablename__ = "browser_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("browser"))
    profile_path: Mapped[str] = mapped_column(String(1024))
    purpose: Mapped[str] = mapped_column(String(120), default="job-applications")
    status: Mapped[str] = mapped_column(String(40), default="configured")
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class BrowserAction(TimestampMixin, Base):
    __tablename__ = "browser_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("baction"))
    application_id: Mapped[str | None] = mapped_column(ForeignKey("applications.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(1024), default="")
    result: Mapped[str] = mapped_column(String(80), default="recorded")
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class DurableTask(TimestampMixin, Base):
    __tablename__ = "durable_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("task"))
    task_type: Mapped[str] = mapped_column(String(120))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AutomationRun(TimestampMixin, Base):
    __tablename__ = "automation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("run"))
    run_type: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default="started")
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Event(TimestampMixin, Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("event"))
    event_type: Mapped[str] = mapped_column(String(120))
    actor: Mapped[str] = mapped_column(String(80), default="system")
    subject_type: Mapped[str] = mapped_column(String(80), default="")
    subject_id: Mapped[str] = mapped_column(String(120), default="")
    severity: Mapped[str] = mapped_column(String(40), default="info")
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
