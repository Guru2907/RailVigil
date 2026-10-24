import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
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

    # Lifecycle:  awaiting_zone -> queued -> processing -> done | failed
    # A video is `queued` from the moment the upload is accepted. If the
    # server dies mid-job the row stays `processing`; startup recovery puts
    # it back to `queued` (see services/job_queue.py).
    status = Column(String, nullable=False, default="queued", index=True)
    progress = Column(Float, nullable=False, default=0.0)   # 0-100, written at most every PROGRESS_UPDATE_SEC
    attempts = Column(Integer, nullable=False, default=0)   # times processing has STARTED; capped by MAX_JOB_ATTEMPTS
    error = Column(Text, nullable=True)                     # short, user-safe message; traceback only in the log

    zone_json = Column(Text, nullable=True)       # normalized zone points, format and source as JSON
    camera_label = Column(String, nullable=True)
    # Optional camera location (map pin given at upload); incidents are mapped here.
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    duration_sec = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    output_video_path = Column(String, nullable=True)   # annotated result

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    detections = relationship("Detection", back_populates="video", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="video", cascade="all, delete-orphan")
