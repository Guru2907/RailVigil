from sqlalchemy.orm import Session

from app.db.models.incident import Incident


def bulk_create(db: Session, video_id: str, events: list[dict]) -> list[Incident]:
    rows = [Incident(video_id=video_id, **event) for event in events]
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def replace_for_video(db: Session, video_id: str, events: list[dict], commit: bool = True) -> None:
    """Delete the video's existing incidents, then insert `events`.

    Why delete first: a job can be run twice for the same video (the server
    crashed after saving incidents but before marking the video done, then
    recovery re-ran it). Plain inserts would leave duplicates. With
    commit=False the caller can put this and the status change in ONE
    transaction, so either both happen or neither does."""
    db.query(Incident).filter(Incident.video_id == video_id).delete(synchronize_session=False)
    db.add_all([Incident(video_id=video_id, **event) for event in events])
    if commit:
        db.commit()


def list_incidents(db: Session, video_id: str | None = None,
                    event_type: str | None = None, min_risk: float | None = None) -> list[Incident]:
    q = db.query(Incident)
    if video_id:
        q = q.filter(Incident.video_id == video_id)
    if event_type:
        q = q.filter(Incident.event_type == event_type)
    if min_risk is not None:
        q = q.filter(Incident.risk_score >= min_risk)
    return q.order_by(Incident.created_at.desc()).all()


def get_incident(db: Session, incident_id: str) -> Incident | None:
    return db.query(Incident).filter(Incident.id == incident_id).first()
