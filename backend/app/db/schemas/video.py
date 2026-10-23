from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.db.schemas.incident import IncidentOut


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    original_filename: str | None = None
    status: str
    progress: float = 0.0
    camera_label: str | None = None
    error: str | None = None
    created_at: datetime
    output_video_path: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def has_output(self) -> bool:
        return bool(self.output_video_path)


class VideoDetailOut(VideoOut):
    incidents: list[IncidentOut] = []


class ZoneAssignIn(BaseModel):
    zone_points: list[list[float]]
