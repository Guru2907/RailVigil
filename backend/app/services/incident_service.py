"""Business logic for reading incidents. Thin for now -- mostly a
pass-through to the repository -- but this is the layer where you'd add
things like 'only show incidents from the last 24 hours' later without
touching the database access code."""

from sqlalchemy.orm import Session

from app.db.repositories import incident_repository


def list_incidents(db: Session, video_id: str | None = None,
                    event_type: str | None = None, min_risk: float | None = None):
    return incident_repository.list_incidents(db, video_id=video_id, event_type=event_type, min_risk=min_risk)


def get_incident(db: Session, incident_id: str):
    return incident_repository.get_incident(db, incident_id)