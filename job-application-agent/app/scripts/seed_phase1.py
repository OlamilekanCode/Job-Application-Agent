import hashlib
from datetime import UTC, datetime

from sqlalchemy import select

from app.audit import record_event
from app.browser.health import ensure_browser_profile
from app.db.models import (
    Application,
    BrowserSession,
    CandidateFact,
    CandidateProfile,
    Job,
    JobEvidence,
    JobScore,
    JobSnapshot,
)
from app.db.session import SessionLocal
from app.tasks import DurableTaskQueue


SAMPLE_JOB_DESCRIPTION = """
ExampleCo is hiring a remote Python/FastAPI developer for a worldwide contractor role.
The role includes backend APIs, SQL data modeling, test automation, and careful written
communication with an async team. This is a synthetic sample record for Phase 1 only.
"""


def seed() -> None:
    with SessionLocal() as session:
        profile = session.scalar(select(CandidateProfile).limit(1))
        if profile is None:
            profile = CandidateProfile(
                full_name="Aliameen Fatunbi",
                location="Nigeria",
                headline="Software developer",
                settings={"phase": "phase1"},
            )
            session.add(profile)
            session.flush()
            record_event(session, "profile.created", subject_type="candidate_profile", subject_id=profile.id)

        if not session.scalar(select(CandidateFact).where(CandidateFact.profile_id == profile.id)):
            session.add_all(
                [
                    CandidateFact(
                        profile_id=profile.id,
                        category="location",
                        field_name="residence_country",
                        structured_value={"country": "Nigeria"},
                        human_value="Resides in Nigeria",
                        source="user_default",
                        confirmation_state="confirmed",
                        confidence=1.0,
                    ),
                    CandidateFact(
                        profile_id=profile.id,
                        category="preference",
                        field_name="timezone_flexibility",
                        structured_value={"flexible": True, "timezone": "Africa/Lagos"},
                        human_value="Flexible on time-zone overlap while based in Africa/Lagos",
                        source="blueprint",
                        confirmation_state="proposed",
                        confidence=0.7,
                    ),
                ]
            )

        job = session.scalar(select(Job).where(Job.source_identifier == "phase1-sample-python"))
        if job is None:
            job = Job(
                source="phase1_sample",
                source_identifier="phase1-sample-python",
                canonical_url="https://example.invalid/jobs/phase1-sample-python",
                company="ExampleCo",
                title="Remote Python/FastAPI Developer",
                location="Worldwide",
                remote_policy="worldwide_contractor",
                status="scored",
                raw_data={"synthetic": True},
            )
            session.add(job)
            session.flush()
            content_hash = hashlib.sha256(SAMPLE_JOB_DESCRIPTION.encode("utf-8")).hexdigest()
            session.add_all(
                [
                    JobSnapshot(
                        job_id=job.id,
                        content_hash=content_hash,
                        content_text=SAMPLE_JOB_DESCRIPTION.strip(),
                        metadata_={"synthetic": True, "captured_at": datetime.now(UTC).isoformat()},
                    ),
                    JobEvidence(
                        job_id=job.id,
                        category="eligibility",
                        evidence_text="Synthetic sample says worldwide contractor role.",
                        source_url=job.canonical_url,
                        confidence="high",
                    ),
                    JobScore(
                        job_id=job.id,
                        total_score=78,
                        components={
                            "stack_match": 24,
                            "experience_match": 16,
                            "role_match": 12,
                            "compensation_quality": 6,
                            "remote_route_confidence": 10,
                            "freshness": 8,
                            "company_credibility": 2,
                        },
                        penalties=[],
                        explanation="Synthetic Phase 1 sample job with eligible worldwide contractor evidence.",
                    ),
                ]
            )
            app = Application(
                job_id=job.id,
                state="scored",
                idempotency_key="phase1-sample-application",
            )
            session.add(app)
            session.flush()
            record_event(session, "sample_job.created", subject_type="job", subject_id=job.id)

        profile_path = ensure_browser_profile()
        if not session.scalar(select(BrowserSession).limit(1)):
            session.add(BrowserSession(profile_path=str(profile_path)))

        DurableTaskQueue().enqueue(
            session,
            "sample_job.score",
            {"job_source_identifier": "phase1-sample-python"},
            idempotency_key="phase1-sample-score-task",
        )

        session.commit()


def main() -> None:
    seed()
    print("Seeded Phase 1 profile, facts, sample job, browser profile, and task queue.")


if __name__ == "__main__":
    main()

