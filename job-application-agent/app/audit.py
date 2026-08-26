from typing import Any

import structlog
from sqlalchemy.orm import Session

from app.db.models import Event

logger = structlog.get_logger(__name__)


def record_event(
    session: Session,
    event_type: str,
    *,
    actor: str = "system",
    subject_type: str = "",
    subject_id: str = "",
    severity: str = "info",
    data: dict[str, Any] | None = None,
) -> Event:
    event = Event(
        event_type=event_type,
        actor=actor,
        subject_type=subject_type,
        subject_id=subject_id,
        severity=severity,
        data=data or {},
    )
    session.add(event)
    logger.info(
        "audit_event",
        event_type=event_type,
        actor=actor,
        subject_type=subject_type,
        subject_id=subject_id,
        severity=severity,
    )
    return event

