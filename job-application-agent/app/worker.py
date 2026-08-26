import asyncio
from collections.abc import Awaitable, Callable
from uuid import uuid4

import structlog
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import DurableTask
from app.db.session import SessionLocal
from app.tasks import DurableTaskQueue

logger = structlog.get_logger(__name__)

TaskHandler = Callable[[Session, DurableTask], Awaitable[dict[str, object]]]


async def phase1_noop_handler(_session: Session, task: DurableTask) -> dict[str, object]:
    await asyncio.sleep(0)
    return {"handled": True, "task_type": task.task_type, "payload": task.payload}


class LocalWorker:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.worker_id = f"worker-{uuid4().hex[:8]}"
        self.queue = DurableTaskQueue(self.settings)
        self.handlers: dict[str, TaskHandler] = {
            "phase1.health_tick": phase1_noop_handler,
            "sample_job.score": phase1_noop_handler,
        }
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self.started = False
        self.last_error: str | None = None
        self.processed_count = 0

    def register_handler(self, task_type: str, handler: TaskHandler) -> None:
        self.handlers[task_type] = handler

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self.run(), name="local-worker")
        self.started = True

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task

    async def run(self) -> None:
        logger.info("worker_started", worker_id=self.worker_id)
        while not self._stop_event.is_set():
            try:
                handled = await self.run_once()
                if not handled:
                    await asyncio.sleep(self.settings.worker_poll_seconds)
            except Exception as exc:  # pragma: no cover - defensive loop guard
                self.last_error = str(exc)
                logger.exception("worker_loop_error", worker_id=self.worker_id)
                await asyncio.sleep(self.settings.worker_poll_seconds)
        logger.info("worker_stopped", worker_id=self.worker_id)

    async def run_once(self) -> bool:
        with SessionLocal() as session:
            task = self.queue.lease_next(session, self.worker_id)
            session.commit()

        if task is None:
            return False

        handler = self.handlers.get(task.task_type)
        with SessionLocal() as session:
            task = session.get(DurableTask, task.id)
            if task is None:
                return False
            try:
                if handler is None:
                    raise RuntimeError(f"No handler registered for task type {task.task_type}")
                result = await handler(session, task)
                self.queue.complete(session, task, result)
                self.processed_count += 1
            except Exception as exc:
                self.last_error = str(exc)
                self.queue.fail(session, task, str(exc))
            session.commit()
        return True

    def health(self) -> dict[str, object]:
        return {
            "status": "healthy" if self.started and self.last_error is None else "unavailable",
            "worker_id": self.worker_id,
            "started": self.started,
            "processed_count": self.processed_count,
            "last_error": self.last_error,
        }

