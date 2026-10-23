from app.core import config
from app.cv.intrusion.temporal_engine import TemporalEngine

CONFIRM = config.CONFIRM_DWELL_SEC
STEP = 0.1


def _box(x1, y1, x2, y2):
    return (x1, y1, x2, y2)


def test_id_switch_merges_into_one_event():
    engine = TemporalEngine()
    box = _box(10, 10, 50, 80)
    # confirm track 1
    t = 0.0
    while t <= CONFIRM + 0.2:
        engine.observe(1, "person", int(t * 10), t, 0.5, bbox=box)
        t += STEP
    # ID switch: track 1 missing this frame, track 2 overlaps
    engine.observe(2, "person", int(t * 10), t, 0.5, bbox=box)
    assert 1 not in engine.active
    assert 2 in engine.active
    engine.finalize_all()
    assert len(engine.get_closed_events()) == 1


def test_two_concurrent_objects_not_merged():
    engine = TemporalEngine()
    t = 0.0
    while t <= CONFIRM + 0.2:
        engine.observe(1, "person", int(t * 10), t, 0.5, bbox=_box(10, 10, 40, 70))
        engine.observe(2, "person", int(t * 10), t, 0.5, bbox=_box(12, 12, 42, 72))  # high IoU but same frame
        t += STEP
    engine.finalize_all()
    assert len(engine.get_closed_events()) == 2
