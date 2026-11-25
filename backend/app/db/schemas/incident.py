from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


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
    # A path on the server's disk: read from the database, never sent to the
    # client. The image itself is served by GET /incidents/{id}/snapshot.
    snapshot_path: str | None = Field(default=None, exclude=True)
    created_at: datetime

    @computed_field
    @property
    def has_snapshot(self) -> bool:
        return bool(self.snapshot_path)