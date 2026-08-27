import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.audit import record_event
from app.config import Settings, get_settings
from app.db.models import AIRun

SMOKE_SCHEMA_VERSION = "phase1.codex_smoke.v1"
SMOKE_PROMPT_VERSION = "phase1.codex_smoke.v1"

CODEX_SMOKE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["ok"]},
        "summary": {"type": "string"},
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "passed": {"type": "boolean"},
                },
                "required": ["name", "passed"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["status", "summary", "checks"],
    "additionalProperties": False,
}


class SmokeCheck(BaseModel):
    name: str
    passed: bool


class CodexSmokeResponse(BaseModel):
    status: str = Field(pattern="^ok$")
    summary: str
    checks: list[SmokeCheck]


def validate_smoke_response(text: str) -> CodexSmokeResponse:
    data = json.loads(text)
    return CodexSmokeResponse.model_validate(data)


def codex_connection_health() -> dict[str, object]:
    try:
        import openai_codex  # noqa: F401

        return {"status": "available", "package": "openai-codex"}
    except Exception as exc:
        return {"status": "unavailable", "package": "openai-codex", "error": str(exc)}


def run_codex_smoke(session: Session, settings: Settings | None = None) -> AIRun:
    resolved = settings or get_settings()
    ai_run = AIRun(
        task_name="codex_smoke",
        prompt_version=SMOKE_PROMPT_VERSION,
        schema_version=SMOKE_SCHEMA_VERSION,
        model_version=resolved.codex_model,
        input_refs=[],
        validation_state="pending",
    )
    session.add(ai_run)
    session.flush()

    prompt = (
        "Return JSON only. Confirm this local Phase 1 smoke test can produce structured output. "
        "Use status ok, a short summary, and checks for json_schema and no_api_key."
    )

    try:
        from openai_codex import Codex

        with Codex() as codex:
            thread = (
                codex.thread_start(model=resolved.codex_model)
                if resolved.codex_model
                else codex.thread_start()
            )
            result = thread.run(prompt, output_schema=CODEX_SMOKE_OUTPUT_SCHEMA)
            structured = validate_smoke_response((result.final_response or "").strip())
            ai_run.codex_thread_id = thread.id
            ai_run.output = structured.model_dump()
            ai_run.validation_state = "valid"
            ai_run.usage = {"items": len(result.items), "status": str(result.status)}
            record_event(
                session,
                "codex.smoke.valid",
                subject_type="ai_run",
                subject_id=ai_run.id,
                data={"thread_id": thread.id},
            )
    except (ValidationError, json.JSONDecodeError) as exc:
        ai_run.validation_state = "invalid"
        ai_run.error = str(exc)
        record_event(
            session,
            "codex.smoke.invalid",
            subject_type="ai_run",
            subject_id=ai_run.id,
            severity="error",
            data={"error": str(exc)},
        )
    except Exception as exc:
        ai_run.validation_state = "unavailable"
        ai_run.error = str(exc)
        record_event(
            session,
            "codex.smoke.unavailable",
            subject_type="ai_run",
            subject_id=ai_run.id,
            severity="warning",
            data={"error": str(exc)},
        )

    return ai_run


def main() -> None:
    from app.db.session import SessionLocal
    from app.logging_config import configure_logging

    configure_logging()
    with SessionLocal() as session:
        ai_run = run_codex_smoke(session)
        session.commit()
        print(json.dumps({"id": ai_run.id, "validation_state": ai_run.validation_state}, indent=2))


if __name__ == "__main__":
    main()
