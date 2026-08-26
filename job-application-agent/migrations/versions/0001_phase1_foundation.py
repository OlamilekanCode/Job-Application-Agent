"""phase 1 foundation

Revision ID: 0001_phase1
Revises:
Create Date: 2026-08-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_phase1"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "candidate_facts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("profile_id", sa.String(length=64), sa.ForeignKey("candidate_profiles.id")),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("field_name", sa.String(length=120), nullable=False),
        sa.Column("structured_value", sa.JSON(), nullable=False),
        sa.Column("human_value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("confirmation_state", sa.String(length=40), nullable=False),
        sa.Column("sensitivity", sa.String(length=40), nullable=False),
        sa.Column("valid_contexts", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("edit_history", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("source_identifier", sa.String(length=255), nullable=False),
        sa.Column("canonical_url", sa.String(length=1024), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("remote_policy", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("source", "source_identifier", name="uq_jobs_source_id"),
    )
    op.create_table(
        "job_snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id")),
        sa.Column("snapshot_type", sa.String(length=80), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "job_evidence",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id")),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=False),
        sa.Column("confidence", sa.String(length=40), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "job_scores",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id")),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("components", sa.JSON(), nullable=False),
        sa.Column("penalties", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id")),
        sa.Column("state", sa.String(length=80), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
    )
    op.create_table(
        "application_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.id")),
        sa.Column("actor", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("conversation_id", sa.String(length=64), sa.ForeignKey("conversations.id")),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("codex_thread_id", sa.String(length=255), nullable=True),
        sa.Column("task_name", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=120), nullable=True),
        sa.Column("input_refs", sa.JSON(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("validation_state", sa.String(length=40), nullable=False),
        sa.Column("usage", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        *timestamps(),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("profile_id", sa.String(length=64), sa.ForeignKey("candidate_profiles.id"), nullable=True),
        sa.Column("document_type", sa.String(length=80), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("immutable", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "browser_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("profile_path", sa.String(length=1024), nullable=False),
        sa.Column("purpose", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "browser_actions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("action_type", sa.String(length=120), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("result", sa.String(length=80), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "durable_tasks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_type", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), unique=True, nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "automation_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("run_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("actor", sa.String(length=80), nullable=False),
        sa.Column("subject_type", sa.String(length=80), nullable=False),
        sa.Column("subject_id", sa.String(length=120), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        *timestamps(),
    )


def downgrade() -> None:
    for table_name in (
        "events",
        "automation_runs",
        "durable_tasks",
        "browser_actions",
        "browser_sessions",
        "documents",
        "ai_runs",
        "conversation_messages",
        "conversations",
        "application_events",
        "applications",
        "job_scores",
        "job_evidence",
        "job_snapshots",
        "jobs",
        "candidate_facts",
        "candidate_profiles",
    ):
        op.drop_table(table_name)

