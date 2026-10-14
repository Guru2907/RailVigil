"""
Adds tracking on top of detection: instead of just "I see a person",
we get "I see person #17", where that same ID keeps showing up across
frames as long as it's the same physical person. This is what lets us
later measure how LONG an object stayed in the safety zone.

Reuses the same YOLO model Detector already loaded -- .track() and
.predict() are just two different modes of the same underlying model,
so we don't want to load the weights file twice.
"""

from app.core import config
from app.cv.detector import Detector


class Tracker:
    def __init__(self, detector: Detector | None = None):
        self.detector = detector or Detector()
        self.model = self.detector.model
        self.class_names = self.detector.class_names

    def reset(self) -> None:
        """Forget all tracking state, ready for a NEW video.

        `model.track(persist=True)` keeps ByteTrack's memory (which boxes
        belong to which id) on the model's `predictor` between calls. That
        is what we want within ONE video, but if a worker reuses this
        Tracker for the next video, ids and half-tracked objects from the
        previous video would leak into it. Dropping the predictor makes
        Ultralytics build a fresh one (with a fresh ByteTrack) on the next
        call. The loaded weights live on `model.model`, so this is cheap:
        nothing is re-read from disk."""
        self.model.predictor = None

    def track(self, frame) -> list[dict]:
        """Runs detection + tracking together on one frame. Same shape
        of output as Detector.detect(), but each dict now also has a
        track_id that stays consistent across frames of the same video."""
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=config.CONF_THRESHOLD,
            verbose=False,
        )
        r = results[0]
        tracked = []

        if r.boxes is None or r.boxes.id is None:
            return tracked

        boxes = r.boxes.xyxy.cpu().numpy()
        cls_ids = r.boxes.cls.cpu().numpy().astype(int)
        confs = r.boxes.conf.cpu().numpy()
        track_ids = r.boxes.id.cpu().numpy().astype(int)

        for box, cid, conf, tid in zip(boxes, cls_ids, confs, track_ids):
            cls_name = self.class_names.get(int(cid), str(cid))
            if cls_name not in config.RELEVANT_CLASSES:
                continue

            x1, y1, x2, y2 = box.tolist()
            tracked.append({
                "track_id": int(tid),
                "class_name": cls_name,
                "confidence": float(conf),
                "bbox": (x1, y1, x2, y2),
            })

        return tracked