from types import SimpleNamespace

import numpy as np

from app.cv.common.detector import Detector
from app.cv.common.tracker import Tracker


def test_reset_drops_the_predictor_so_tracking_state_starts_fresh():
    """Ultralytics keeps ByteTrack's memory on model.predictor. Clearing it
    is what stops ids from one video leaking into the next one."""
    tracker = Tracker.__new__(Tracker)          # skip __init__: it would load real weights
    tracker.model = SimpleNamespace(predictor=object())

    tracker.reset()

    assert tracker.model.predictor is None


def test_reset_is_safe_before_any_tracking_has_happened():
    tracker = Tracker.__new__(Tracker)
    tracker.model = SimpleNamespace(predictor=None)
    tracker.reset()
    assert tracker.model.predictor is None


def test_tracker_class_filter_is_configurable():
    class Tensor:
        def __init__(self, values):
            self.values = np.asarray(values)

        def cpu(self):
            return self

        def numpy(self):
            return self.values

    boxes = SimpleNamespace(
        xyxy=Tensor([[0, 0, 10, 10], [1, 1, 11, 11]]),
        cls=Tensor([0, 1]),
        conf=Tensor([0.9, 0.8]),
        id=Tensor([1, 2]),
    )
    model = SimpleNamespace(track=lambda *args, **kwargs: [SimpleNamespace(boxes=boxes)])
    tracker = Tracker.__new__(Tracker)
    tracker.model = model
    tracker.class_names = {0: "person", 1: "car"}
    tracker.class_filter = frozenset({"person"})

    assert [obj["class_name"] for obj in tracker.track(None)] == ["person"]


def test_detector_class_filter_is_configurable(monkeypatch):
    class Tensor:
        def __init__(self, values):
            self.values = np.asarray(values)

        def cpu(self):
            return self

        def numpy(self):
            return self.values

    boxes = SimpleNamespace(
        xyxy=Tensor([[0, 0, 10, 10], [1, 1, 11, 11]]),
        cls=Tensor([0, 1]),
        conf=Tensor([0.9, 0.8]),
    )

    class Model:
        names = {0: "person", 1: "tree"}

        def predict(self, *args, **kwargs):
            return [SimpleNamespace(boxes=boxes)]

    monkeypatch.setattr("app.cv.common.detector.YOLO", lambda _weights: Model())
    detector = Detector(class_filter={"tree"})

    assert [item["class_name"] for item in detector.detect(None)] == ["tree"]
