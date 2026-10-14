from types import SimpleNamespace

from app.cv.tracker import Tracker


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
