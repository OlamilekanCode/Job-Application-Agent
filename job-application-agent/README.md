# Job Application Agent

Phase 1 foundation for a private, local-first job application assistant.

This sprint intentionally does not scrape jobs, tailor CVs, submit forms, or visit real
application pages. It creates the local application shell, persistence layer, health checks,
candidate fact editor, sample job data, durable worker queue, Codex smoke test, and a dedicated
Playwright browser profile path.

## Setup

```powershell
cd job-application-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

Authenticate Codex through ChatGPT, not through an OpenAI API key:

```powershell
codex login
```

## Database

```powershell
alembic upgrade head
python -m app.scripts.seed_phase1
```

The default SQLite database is `data/job_application_agent.db`. SQLite is configured with
foreign keys and WAL mode whenever the application connects.

## Run

```powershell
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8010
```

Open `http://127.0.0.1:8010`.

## Checks

```powershell
pytest
python -m app.ai.smoke
```

The Codex smoke test uses the `openai-codex` Python SDK with the existing ChatGPT/Codex login
session. It does not read or require `OPENAI_API_KEY`.

## Phase 1 Boundaries

- Original CV files are only intended to be preserved as immutable records in later import work.
- No CV rewriting, tailoring, or rearrangement is implemented.
- Playwright is configured for a dedicated local profile, but no real job site is opened.
- Final submission automation is out of scope.

