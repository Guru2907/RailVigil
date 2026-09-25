from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services import incident_service


def get_incidents(db: Session, video_id=None, event_type=None, min_risk=None):
    return incident_service.list_incidents(db, video_id=video_id, event_type=event_type, min_risk=min_risk)


def get_incident_detail(db: Session, incident_id: str):
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident