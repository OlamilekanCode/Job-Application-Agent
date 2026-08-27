import sys
import types

from sqlalchemy.orm import sessionmaker

from app.ai.smoke import run_codex_smoke, validate_smoke_response
from app.config import Settings
from app.db.models import AIRun, Base, Event
from app.db.session import create_engine_for_settings


def test_validate_smoke_response_accepts_schema_valid_json():
    result = validate_smoke_response(
        '{"status":"ok","summary":"ready","checks":[{"name":"json_schema","passed":true}]}'
    )
    assert result.status == "ok"
    assert result.checks[0].passed is True


def test_run_codex_smoke_records_valid_ai_run_with_fake_sdk(tmp_path, monkeypatch):
    class FakeResult:
        final_response = (
            '{"status":"ok","summary":"structured output works",'
            '"checks":[{"name":"json_schema","passed":true},{"name":"no_api_key","passed":true}]}'
        )
        items = []
        status = "completed"

    class FakeThread:
        id = "thr_fake"

        def run(self, prompt, output_schema=None):
            assert "Return JSON only" in prompt
            assert output_schema is not None
            return FakeResult()

    class FakeCodex:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def thread_start(self, **kwargs):
            return FakeThread()

    fake_module = types.SimpleNamespace(Codex=FakeCodex)
    monkeypatch.setitem(sys.modules, "openai_codex", fake_module)

    settings = Settings(database_url=f"sqlite:///{tmp_path / 'codex.db'}")
    settings.ensure_local_paths()
    engine = create_engine_for_settings(settings)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        ai_run = run_codex_smoke(session, settings)
        session.commit()
        ai_run_id = ai_run.id

    with session_factory() as session:
        persisted = session.get(AIRun, ai_run_id)
        assert persisted is not None
        assert persisted.validation_state == "valid"
        assert persisted.codex_thread_id == "thr_fake"
        assert persisted.output["status"] == "ok"
        assert session.query(Event).filter_by(event_type="codex.smoke.valid").count() == 1

