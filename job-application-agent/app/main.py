from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.db.session import SessionLocal
from app.logging_config import configure_logging
from app.scheduler import create_scheduler, enqueue_health_tick
from app.web.routes import router
from app.worker import LocalWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    worker = LocalWorker(settings)
    scheduler = create_scheduler()
    app.state.worker = worker
    app.state.scheduler = scheduler

    await worker.start()

    def scheduled_health_tick() -> None:
        with SessionLocal() as session:
            enqueue_health_tick(session)
            session.commit()

    scheduler.add_job(scheduled_health_tick, "interval", minutes=5, id="phase1_health_tick")
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await worker.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="Job Application Agent", lifespan=lifespan)
    app.state.templates = Jinja2Templates(directory="app/web/templates")
    app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
    app.include_router(router)
    return app


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )

