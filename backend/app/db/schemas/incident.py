from datetime import datetime
from pydantic import BaseModel, ConfigDict


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    video_id: str
    track_id: int
    object_class: str
    event_type: str
    severity: str
    is_persistent: bool
    start_frame: int
    end_frame: int
    start_ts: float
    end_ts: float
    dwell_time_sec: float
    max_penetration: float
    avg_penetration: float
    risk_score: float
    zone_label: str
    snapshot_path: str | None = None
    created_at: datetime