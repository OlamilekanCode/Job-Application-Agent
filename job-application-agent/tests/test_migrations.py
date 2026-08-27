from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import get_settings


def test_phase1_migration_creates_core_tables_and_wal(tmp_path, monkeypatch):
    db_path = tmp_path / "phase1.db"
    monkeypatch.setenv("JAA_DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    table_names = set(inspect(engine).get_table_names())
    assert {
        "candidate_profiles",
        "candidate_facts",
        "jobs",
        "job_evidence",
        "job_scores",
        "applications",
        "ai_runs",
        "durable_tasks",
        "events",
        "browser_sessions",
    }.issubset(table_names)

    with engine.connect() as connection:
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
    assert journal_mode == "wal"

    get_settings.cache_clear()

