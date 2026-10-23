"""The encroachment decision rule (docs/ENCROACHMENT_SPEC.md).

A detection becomes a *potential* encroachment finding when it is confident
enough and enough of it lies inside the railway zone. Its severity comes from
how serious its category is and how much of it is inside:

    overlap_ratio  = area(object ∩ zone) / area(object)
    severity_score = category_weight × overlap_ratio      (0-1)
    severity       = band of severity_score (critical / high / medium / low)

Severity says how serious the object would be if it is really there;
confidence says how sure the model is that it is. A low-confidence finding
keeps its severity but gets a note so a reviewer does not mistake the two.

Pure functions only: no models, files or I/O, so every case is unit-tested.
"""

from dataclasses import dataclass, field

from app.core import config
from app.cv.encroachment.detector import Detection
from app.cv.encroachment.geometry import box_polygon, overlap_ratio
from app.cv.encroachment.taxonomy import VEHICLE_PARKED

SEVERITY_ORDER = ("low", "medium", "high", "critical")


@dataclass(frozen=True)
class RuleConfig:
    min_confidence: float
    min_overlap: float
    category_weight: dict
    severity_bands: dict
    vehicle_max_severity: str
    low_confidence_note: float = 0.0

    @classmethod
    def from_settings(cls) -> "RuleConfig":
        return cls(
            min_confidence=config.ENC_MIN_CONFIDENCE,
            min_overlap=config.ENC_MIN_OVERLAP,
            category_weight=dict(config.ENC_CATEGORY_WEIGHT),
            severity_bands=dict(config.ENC_SEVERITY_BANDS),
            vehicle_max_severity=config.ENC_VEHICLE_MAX_SEVERITY,
            low_confidence_note=config.ENC_LOW_CONFIDENCE_NOTE,
        )


@dataclass
class Finding:
    cls: str
    label: str
    confidence: float
    bbox: tuple[float, float, float, float]
    sources: list[str]
    zone_hit: str                 # which zone it is in; "Z3" = right-of-way polygon (Phase 1)
    overlap_ratio: float          # share of the object inside the zone, 0-1
    overlap_area_px: float
    severity_score: float
    severity: str
    notes: list[str] = field(default_factory=list)


def severity_for(score: float, bands: dict) -> str:
    for level in ("critical", "high", "medium"):
        if score >= bands[level]:
            return level
    return "low"


def classify_finding(det: Detection, zone, cfg: RuleConfig, zone_name: str = "Z3") -> Finding | None:
    """A Finding if `det` is a potential encroachment inside `zone` (a shapely
    polygon in image pixels), otherwise None."""
    if det.confidence < cfg.min_confidence:
        return None
    ratio, area = overlap_ratio(box_polygon(det.bbox), zone)
    if ratio < cfg.min_overlap:
        return None

    score = cfg.category_weight.get(det.cls, 0.0) * ratio
    severity = severity_for(score, cfg.severity_bands)
    notes = []
    if det.confidence < cfg.low_confidence_note:
        notes.append("low detection confidence - verify the object is really there")
    if det.cls == VEHICLE_PARKED:
        notes.append("stationarity not verified from a single image")
        cap = cfg.vehicle_max_severity
        if SEVERITY_ORDER.index(severity) > SEVERITY_ORDER.index(cap):
            severity = cap

    return Finding(
        cls=det.cls, label=det.label, confidence=round(det.confidence, 4), bbox=det.bbox,
        sources=list(det.sources), zone_hit=zone_name,
        overlap_ratio=round(ratio, 4), overlap_area_px=round(area, 1),
        severity_score=round(score, 4), severity=severity, notes=notes,
    )
