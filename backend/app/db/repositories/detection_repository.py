from sqlalchemy.orm import Session

from app.db.models.detection import Detection


def create_detection(db: Session, video_id: str, detection: dict) -> Detection:
    row = Detection(video_id=video_id, **detection)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_detections(db: Session, video_id: str) -> list[Detection]:
    return db.query(Detection).filter(Detection.video_id == video_id).all()