"""
YOLOv8 wrapper. Its only job: given a frame, tell you what objects YOLO
sees, filtered to the classes we actually care about for railway
encroachment. No tracking (tracker.py), no zone logic (zone_engine.py)
here — this file does one thing.
"""

from ultralytics import YOLO

from app.core import config


class Detector:
    def __init__(self, weights_path: str | None = None):
        self.model = YOLO(weights_path or config.MODEL_WEIGHTS)
        self.class_names = self.model.names  # {0: "person", 1: "bicycle", ...}

    def detect(self, frame) -> list[dict]:
        """Single-frame detection, no track IDs. Returns a list of dicts:
        {class_name, confidence, bbox: (x1, y1, x2, y2)}
        filtered to config.RELEVANT_CLASSES and config.CONF_THRESHOLD."""
        results = self.model.predict(
            frame, conf=config.CONF_THRESHOLD, verbose=False
        )
        r = results[0]
        detections = []

        if r.boxes is None:
            return detections

        boxes = r.boxes.xyxy.cpu().numpy()
        cls_ids = r.boxes.cls.cpu().numpy().astype(int)
        confs = r.boxes.conf.cpu().numpy()

        for box, cid, conf in zip(boxes, cls_ids, confs):
            cls_name = self.class_names.get(int(cid), str(cid))
            if cls_name not in config.RELEVANT_CLASSES:
                continue
            x1, y1, x2, y2 = box.tolist()
            detections.append({
                "class_name": cls_name,
                "confidence": float(conf),
                "bbox": (x1, y1, x2, y2),
            })

        return detections