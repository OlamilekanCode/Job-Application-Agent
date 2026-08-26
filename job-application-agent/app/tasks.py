from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.config import Settings, get_settings
from app.db.models import DurableTask


def now_utc() -> datetime:
    return datetime.now(UTC)


class DurableTaskQueue:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def enqueue(
        self,
        session: Session,
        task_type: str,
        payload: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
        next_run_at: datetime | None = None,
        max_attempts: int = 3,
    ) -> DurableTask:
        if idempotency_key:
            existing = session.scalar(
                select(DurableTask).where(DurableTask.idempotency_key == idempotency_key)
            )
            if existing:
                return existing

        task = DurableTask(
            task_type=task_type,
            payload=payload or {},
            idempotency_key=idempotency_key,
            next_run_at=next_run_at or now_utc(),
            max_attempts=max_attempts,
        )
        session.add(task)
        session.flush()
        record_event(
            session,
            "task.enqueued",
            subject_type="durable_task",
            subject_id=task.id,
            data={"task_type": task_type},
        )
        return task

    def _claimable_query(self) -> Select[tuple[DurableTask]]:
        current = now_utc()
        return (
            select(DurableTask)
            .where(
                DurableTask.next_run_at <= current,
                DurableTask.attempts < DurableTask.max_attempts,
                or_(
                    DurableTask.status.in_(["queued", "retry"]),
                    and_(
                        DurableTask.status == "running",
                        DurableTask.lease_expires_at.is_not(None),
                        DurableTask.lease_expires_at <= current,
                    ),
                ),
            )
            .order_by(DurableTask.next_run_at.asc(), DurableTask.created_at.asc())
            .limit(1)
        )

    def lease_next(self, session: Session, worker_id: str) -> DurableTask | None:
        task = session.scalar(self._claimable_query())
        if task is None:
            return None

        task.status = "running"
        task.attempts += 1
        task.locked_by = worker_id
        task.lease_expires_at = now_utc() + timedelta(seconds=self.settings.task_lease_seconds)
        session.flush()
        record_event(
            session,
            "task.leased",
            subject_type="durable_task",
            subject_id=task.id,
            data={"task_type": task.task_type, "worker_id": worker_id, "attempts": task.attempts},
        )
        return task

    def complete(self, session: Session, task: DurableTask, result: dict[str, Any] | None = None) -> None:
        task.status = "completed"
        task.result = result or {}
        task.lease_expires_at = None
        task.locked_by = None
        task.last_error = None
        record_event(
            session,
            "task.completed",
            subject_type="durable_task",
            subject_id=task.id,
            data={"task_type": task.task_type},
        )

    def fail(self, session: Session, task: DurableTask, error: str) -> None:
        retryable = task.attempts < task.max_attempts
        task.status = "retry" if retryable else "failed"
        task.last_error = error
        task.next_run_at = now_utc() + timedelta(seconds=min(300, 10 * max(task.attempts, 1)))
        task.lease_expires_at = None
        task.locked_by = None
        record_event(
            session,
            "task.failed",
            subject_type="durable_task",
            subject_id=task.id,
            severity="warning" if retryable else "error",
            data={"task_type": task.task_type, "retryable": retryable, "error": error},
        )

    def summary(self, session: Session) -> dict[str, int]:
        rows = session.query(DurableTask.status, DurableTask.id).all()
        counts: dict[str, int] = {}
        for status, _task_id in rows:
            counts[status] = counts.get(status, 0) + 1
        return counts

