from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.db.models import CandidateFact, CandidateProfile, Event, Job, JobEvidence, JobScore
from app.db.session import get_session
from app.health import collect_health
from app.tasks import DurableTaskQueue

router = APIRouter()


def templates(request: Request):
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    jobs = session.scalars(select(Job).order_by(Job.created_at.desc()).limit(5)).all()
    events = session.scalars(select(Event).order_by(Event.created_at.desc()).limit(8)).all()
    facts = session.scalars(select(CandidateFact).order_by(CandidateFact.created_at.desc()).limit(5)).all()
    return templates(request).TemplateResponse(
        request,
        "dashboard.html",
        {
            "jobs": jobs,
            "events": events,
            "facts": facts,
            "task_summary": DurableTaskQueue().summary(session),
        },
    )


@router.get("/health", response_class=HTMLResponse)
def health_page(request: Request, session: Session = Depends(get_session)):
    return templates(request).TemplateResponse(
        request,
        "health.html",
        {
            "health": collect_health(
                session,
                worker=request.app.state.worker,
                scheduler=request.app.state.scheduler,
            )
        },
    )


@router.get("/api/health")
def health_api(request: Request, session: Session = Depends(get_session)):
    return collect_health(
        session,
        worker=request.app.state.worker,
        scheduler=request.app.state.scheduler,
    )


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, session: Session = Depends(get_session)):
    profile = session.scalar(select(CandidateProfile).limit(1))
    facts = session.scalars(select(CandidateFact).order_by(CandidateFact.created_at.desc())).all()
    return templates(request).TemplateResponse(
        request,
        "profile.html",
        {"profile": profile, "facts": facts},
    )


@router.post("/profile")
def update_profile(
    full_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    location: str = Form("Nigeria"),
    headline: str = Form(""),
    session: Session = Depends(get_session),
):
    profile = session.scalar(select(CandidateProfile).limit(1))
    if profile is None:
        profile = CandidateProfile()
        session.add(profile)
        session.flush()
    profile.full_name = full_name.strip()
    profile.email = email.strip()
    profile.phone = phone.strip()
    profile.location = location.strip() or "Nigeria"
    profile.headline = headline.strip()
    record_event(session, "profile.updated", actor="user", subject_type="candidate_profile", subject_id=profile.id)
    session.commit()
    return RedirectResponse("/profile", status_code=303)


@router.post("/facts")
def create_fact(
    category: str = Form(...),
    field_name: str = Form(...),
    human_value: str = Form(...),
    source: str = Form(...),
    confirmation_state: str = Form("proposed"),
    sensitivity: str = Form("normal"),
    session: Session = Depends(get_session),
):
    profile = session.scalar(select(CandidateProfile).limit(1))
    if profile is None:
        profile = CandidateProfile(location="Nigeria")
        session.add(profile)
        session.flush()
    fact = CandidateFact(
        profile_id=profile.id,
        category=category.strip(),
        field_name=field_name.strip(),
        human_value=human_value.strip(),
        structured_value={"value": human_value.strip()},
        source=source.strip(),
        confirmation_state=confirmation_state,
        sensitivity=sensitivity,
        confidence=1.0 if confirmation_state == "confirmed" else 0.5,
    )
    session.add(fact)
    session.flush()
    record_event(session, "fact.created", actor="user", subject_type="candidate_fact", subject_id=fact.id)
    session.commit()
    return RedirectResponse("/profile", status_code=303)


@router.post("/facts/{fact_id}/confirm")
def confirm_fact(fact_id: str, session: Session = Depends(get_session)):
    fact = session.get(CandidateFact, fact_id)
    if fact is not None:
        fact.edit_history = [
            *fact.edit_history,
            {"at": datetime.now(UTC).isoformat(), "action": "confirmed", "from": fact.confirmation_state},
        ]
        fact.confirmation_state = "confirmed"
        fact.confidence = 1.0
        record_event(session, "fact.confirmed", actor="user", subject_type="candidate_fact", subject_id=fact.id)
        session.commit()
    return RedirectResponse("/profile", status_code=303)


@router.post("/facts/{fact_id}/disable")
def disable_fact(fact_id: str, session: Session = Depends(get_session)):
    fact = session.get(CandidateFact, fact_id)
    if fact is not None:
        fact.disabled_at = datetime.now(UTC)
        fact.edit_history = [
            *fact.edit_history,
            {"at": fact.disabled_at.isoformat(), "action": "disabled"},
        ]
        record_event(session, "fact.disabled", actor="user", subject_type="candidate_fact", subject_id=fact.id)
        session.commit()
    return RedirectResponse("/profile", status_code=303)


@router.get("/jobs", response_class=HTMLResponse)
def jobs_page(request: Request, session: Session = Depends(get_session)):
    jobs = session.scalars(select(Job).order_by(Job.created_at.desc())).all()
    evidence_by_job = {
        job.id: session.scalars(select(JobEvidence).where(JobEvidence.job_id == job.id)).all()
        for job in jobs
    }
    scores_by_job = {
        job.id: session.scalar(select(JobScore).where(JobScore.job_id == job.id))
        for job in jobs
    }
    return templates(request).TemplateResponse(
        request,
        "jobs.html",
        {"jobs": jobs, "evidence_by_job": evidence_by_job, "scores_by_job": scores_by_job},
    )


@router.get("/events", response_class=HTMLResponse)
def events_page(request: Request, session: Session = Depends(get_session)):
    events = session.scalars(select(Event).order_by(Event.created_at.desc()).limit(100)).all()
    return templates(request).TemplateResponse(request, "events.html", {"events": events})

