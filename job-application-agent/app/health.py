from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.ai.smoke import codex_connection_health
from app.browser.health import playwright_health
from app.db.session import check_database
from app.scheduler import scheduler_health
from app.tasks import DurableTaskQueue
from app.worker import LocalWorker


def collect_health(
    session: Session,
    *,
    worker: LocalWorker | None = None,
    scheduler: AsyncIOScheduler | None = None,
) -> dict[str, object]:
    health: dict[str, object] = {
        "database": check_database(session),
        "worker": worker.health() if worker else {"status": "unavailable", "started": False},
        "scheduler": scheduler_health(scheduler),
        "codex": codex_connection_health(),
        "playwright": playwright_health(),
        "tasks": DurableTaskQueue().summary(session),
    }
    statuses = [
        part.get("status")
        for part in health.values()
        if isinstance(part, dict) and "status" in part
    ]
    health["overall"] = "healthy" if all(status in {"healthy", "available", "configured"} for status in statuses) else "degraded"
    return health

