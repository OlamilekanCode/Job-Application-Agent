from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import Base
from app.db.session import create_engine_for_settings
from app.health import collect_health


class DummyWorker:
    def health(self):
        return {"status": "healthy", "started": True, "processed_count": 0}


class DummyScheduler:
    running = True

    def get_jobs(self):
        return ["job"]


def test_collect_health_reports_core_components(tmp_path, monkeypatch):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'health.db'}")
    settings.ensure_local_paths()
    engine = create_engine_for_settings(settings)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    monkeypatch.setattr("app.health.codex_connection_health", lambda: {"status": "available"})
    monkeypatch.setattr("app.health.playwright_health", lambda: {"status": "configured"})

    with session_factory() as session:
        health = collect_health(session, worker=DummyWorker(), scheduler=DummyScheduler())

    assert health["overall"] == "healthy"
    assert health["database"]["status"] == "healthy"
    assert health["database"]["journal_mode"] == "wal"
    assert health["worker"]["status"] == "healthy"
    assert health["scheduler"]["status"] == "healthy"
    assert health["codex"]["status"] == "available"
    assert health["playwright"]["status"] == "configured"

