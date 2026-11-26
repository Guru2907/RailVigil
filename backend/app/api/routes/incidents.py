from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.controllers import incident_controller
from app.db.database import get_db
from app.db.schemas.incident import IncidentOut
from app.utils.file_utils import find_output_file

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    video_id: str | None = None,
    event_type: str | None = None,
    min_risk: float | None = Query(default=None, ge=0, le=100),
    db: Session = Depends(get_db),
):
    return incident_controller.get_incidents(db, video_id=video_id, event_type=event_type, min_risk=min_risk)


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    return incident_controller.get_incident_detail(db, incident_id)


@router.get("/{incident_id}/snapshot")
def get_incident_snapshot(incident_id: str, db: Session = Depends(get_db)):
    incident = incident_controller.get_incident_detail(db, incident_id)
    path = find_output_file(incident.snapshot_path, incident.video_id)
    if path is None:
        raise HTTPException(status_code=404, detail="No snapshot for this incident")
    return FileResponse(path)