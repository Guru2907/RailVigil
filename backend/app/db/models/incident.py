import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


def _uuid():
    return str(uuid.uuid4())[:8]


class Incident(Base):
    """A CONFIRMED encroachment event — produced once temporal_engine +
    risk_engine decide a tracked object's time inside the zone was
    significant, not just a momentary detection."""

    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=_uuid)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)

    track_id = Column(Integer)
    object_class = Column(String)
    event_type = Column(String)     # human_intrusion | vehicle_intrusion | persistent_human_presence | ...
    severity = Column(String)       # low | medium | high | critical  (derived from risk_score)
    is_persistent = Column(Boolean, default=False)

    start_frame = Column(Integer)
    end_frame = Column(Integer)
    start_ts = Column(Float)        # seconds into the video
    end_ts = Column(Float)
    dwell_time_sec = Column(Float)

    max_penetration = Column(Float)
    avg_penetration = Column(Float)
    risk_score = Column(Float)      # 0-100

    zone_label = Column(String)
    snapshot_path = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    video = relationship("Video", back_populates="incidents")