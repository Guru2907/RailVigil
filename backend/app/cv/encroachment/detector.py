"""Runs the encroachment models on one image and returns detections in
RailVigil's classes (taxonomy.py), with duplicates across models merged."""

from dataclasses import dataclass, field

from app.core import config
from app.cv.common.model_registry import get_model
from app.cv.encroachment.geometry import iou, object_polygon
from app.cv.encroachment.taxonomy import map_label


@dataclass
class Detection:
    cls: str                                   # RailVigil class, e.g. "structure_temporary"
    label: str                                 # the model's own label, e.g. "Tent" or "tin shed"
    confidence: float
    bbox: tuple[float, float, float, float]    # x1, y1, x2, y2 in image pixels
    sources: list[str] = field(default_factory=list)   # "model-name@version"
    outline: list[tuple[float, float]] | None = None   # mask outline in image pixels (segmentation models only)

    def polygon(self):
        return object_polygon(self.bbox, self.outline)


def merge_detections(detections: list[Detection], iou_threshold: float) -> list[Detection]:
    """Two models (or one model twice) reporting the same class on the same
    object become one detection: the most confident one is kept and the
    other's sources are added to it."""
    merged: list[Detection] = []
    for det in sorted(detections, key=lambda d: d.confidence, reverse=True):
        poly = det.polygon()
        for kept in merged:
            if kept.cls == det.cls and iou(kept.polygon(), poly) >= iou_threshold:
                kept.sources.extend(s for s in det.sources if s not in kept.sources)
                break
        else:
            merged.append(Detection(det.cls, det.label, det.confidence, det.bbox, list(det.sources), det.outline))
    return merged


def _outline(points) -> list[tuple[float, float]] | None:
    if points is None or len(points) < 3:
        return None
    return [(float(x), float(y)) for x, y in points]


class EncroachmentDetector:
    def __init__(self, model_names: list[str] | None = None, min_confidence: float | None = None,
                 merge_iou: float | None = None, loader=get_model):
        """min_confidence, if given, applies to every model; otherwise each
        model uses its own cut-off from ENC_MODEL_MIN_CONFIDENCE."""
        self.model_names = model_names or config.ENC_MODELS
        self.min_confidence = min_confidence
        self.merge_iou = config.ENC_MERGE_IOU if merge_iou is None else merge_iou
        self._loader = loader

    def confidence_for(self, model_name: str) -> float:
        if self.min_confidence is not None:
            return self.min_confidence
        return config.ENC_MODEL_MIN_CONFIDENCE.get(model_name, config.ENC_MIN_CONFIDENCE)

    def model_versions(self) -> dict[str, str]:
        return {name: self._loader(name).version for name in self.model_names}

    def detect(self, image_bgr) -> list[Detection]:
        height, width = image_bgr.shape[:2]
        max_box_area = config.ENC_MAX_BOX_SHARE * width * height
        found: list[Detection] = []
        for name in self.model_names:
            loaded = self._loader(name)
            result = loaded.model.predict(image_bgr, conf=self.confidence_for(name), verbose=False)[0]
            if result.boxes is None:
                continue
            names = result.names
            # Segmentation models also return one mask outline per box, in pixels.
            masks = getattr(result, "masks", None)
            outlines = list(masks.xy) if masks is not None else [None] * len(result.boxes.conf.cpu().numpy())
            for xyxy, cls_id, conf, outline in zip(
                result.boxes.xyxy.cpu().numpy(),
                result.boxes.cls.cpu().numpy().astype(int),
                result.boxes.conf.cpu().numpy(),
                outlines,
                strict=True,
            ):
                label = names[int(cls_id)]
                cls = map_label(name, label)
                if cls is None:
                    continue
                x1, y1, x2, y2 = (float(v) for v in xyxy)
                if (x2 - x1) * (y2 - y1) >= max_box_area:
                    continue  # a "box" around the whole photo is not an object
                found.append(Detection(
                    cls=cls, label=label, confidence=float(conf),
                    bbox=tuple(float(v) for v in xyxy),
                    sources=[f"{name}@{loaded.version}"],
                    outline=_outline(outline),
                ))
        return merge_detections(found, self.merge_iou)
