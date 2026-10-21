import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


def _uuid():
    return str(uuid.uuid4())[:8]


class Detection(Base):
    """A single YOLO+tracker observation of one object in one sampled
    frame. Lower-level than Incident — most detections never become an
    incident (an object just passing by outside the zone, for example).

    NOTE: we intentionally do NOT persist every detection from every
    sampled frame — that would bloat SQLite fast on a multi-minute
    video. video_processor.py should only write a Detection row when the
    object is inside the zone (i.e. relevant to an active/confirmed
    track), not for every frame of every object.
    """

    __tablename__ = "detections"

    id = Column(String, primary_key=True, default=_uuid)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)

    frame_idx = Column(Integer, nullable=False)
    timestamp_sec = Column(Float, nullable=False)

    track_id = Column(Integer, nullable=False)
    object_class = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)

    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)

    in_zone = Column(Boolean, default=False)
    penetration_ratio = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    video = relationship("Video", back_populates="detections")