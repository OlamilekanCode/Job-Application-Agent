from datetime import timedelta

from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db.models import Base
from app.db.session import create_engine_for_settings
from app.tasks import DurableTaskQueue, now_utc


def make_session(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'queue.db'}")
    settings.ensure_local_paths()
    engine = create_engine_for_settings(settings)
    Base.metadata.create_all(engine)
    return settings, sessionmaker(bind=engine, expire_on_commit=False)


def test_enqueue_is_idempotent_and_records_event(tmp_path):
    settings, session_factory = make_session(tmp_path)
    queue = DurableTaskQueue(settings)

    with session_factory() as session:
        first = queue.enqueue(session, "phase1.health_tick", {"a": 1}, idempotency_key="same")
        second = queue.enqueue(session, "phase1.health_tick", {"a": 2}, idempotency_key="same")
        session.commit()

        assert first.id == second.id
        assert queue.summary(session) == {"queued": 1}


def test_lease_complete_and_retry_lifecycle(tmp_path):
    settings, session_factory = make_session(tmp_path)
    queue = DurableTaskQueue(settings)

    with session_factory() as session:
        task = queue.enqueue(session, "sample_job.score")
        session.commit()
        task_id = task.id

    with session_factory() as session:
        task = queue.lease_next(session, "worker-a")
        assert task is not None
        assert task.id == task_id
        assert task.status == "running"
        assert task.attempts == 1
        queue.complete(session, task, {"ok": True})
        session.commit()

    with session_factory() as session:
        assert queue.summary(session)["completed"] == 1

    with session_factory() as session:
        task = queue.enqueue(
            session,
            "sample_job.score",
            next_run_at=now_utc() - timedelta(seconds=1),
            max_attempts=2,
        )
        session.commit()

    with session_factory() as session:
        task = queue.lease_next(session, "worker-b")
        assert task is not None
        queue.fail(session, task, "temporary")
        session.commit()
        assert task.status == "retry"
        assert task.last_error == "temporary"

