import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


def _uuid():
    return str(uuid.uuid4())[:8]


class Video(Base):
    """One uploaded video and its processing state. The 'job' the
    frontend polls while YOLO + tracking + zone/temporal/risk logic run
    on it in the background."""

    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=_uuid)
    filename = Column(String, nullable=False)           # stored filename on disk
    original_filename = Column(String, nullable=True)   # what the user uploaded

    status = Column(String, default="uploaded")  # uploaded | processing | done | failed
    error = Column(Text, nullable=True)

    zone_json = Column(Text, nullable=True)       # safety-zone polygon, as JSON text
    camera_label = Column(String, nullable=True)

    duration_sec = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    output_video_path = Column(String, nullable=True)   # annotated result

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    detections = relationship("Detection", back_populates="video", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="video", cascade="all, delete-orphan")