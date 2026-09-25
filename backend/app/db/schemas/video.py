from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.db.schemas.incident import IncidentOut


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    original_filename: str | None = None
    status: str
    camera_label: str | None = None
    output_video_path: str | None = None
    error: str | None = None
    created_at: datetime


class VideoDetailOut(VideoOut):
    incidents: list[IncidentOut] = []