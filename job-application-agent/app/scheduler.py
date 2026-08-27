from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.tasks import DurableTaskQueue


def create_scheduler() -> AsyncIOScheduler:
    return AsyncIOScheduler(timezone="UTC")


def enqueue_health_tick(session: Session) -> None:
    queue = DurableTaskQueue()
    queue.enqueue(
        session,
        "phase1.health_tick",
        {"created_by": "scheduler", "created_at": datetime.now(UTC).isoformat()},
        idempotency_key=f"phase1-health-{datetime.now(UTC).strftime('%Y%m%d%H%M')}",
    )


def scheduler_health(scheduler: AsyncIOScheduler | None) -> dict[str, object]:
    if scheduler is None:
        return {"status": "unavailable", "running": False, "jobs": 0}
    return {
        "status": "healthy" if scheduler.running else "unavailable",
        "running": scheduler.running,
        "jobs": len(scheduler.get_jobs()),
    }

