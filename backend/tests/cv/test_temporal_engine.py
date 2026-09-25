import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.cv.temporal_engine import TemporalEngine
from app.core import config


def test_short_visit_is_not_confirmed():
    """Object seen inside the zone for fewer frames than the
    confirmation threshold should never get confirmed."""
    engine = TemporalEngine()
    for frame_idx in range(config.CONSECUTIVE_FRAMES_THRESHOLD - 1):
        engine.observe(track_id=1, object_class="person", frame_idx=frame_idx,
                        ts_sec=frame_idx * 0.1, penetration=0.5)
    engine.finalize_missing(seen_track_ids=set())  # object leaves
    assert len(engine.get_closed_events()) == 0


def test_long_visit_is_confirmed_and_closed_on_exit():
    """Object seen for MORE frames than the threshold should get
    confirmed, and closed out once it's no longer seen."""
    engine = TemporalEngine()
    for frame_idx in range(config.CONSECUTIVE_FRAMES_THRESHOLD + 3):
        engine.observe(track_id=7, object_class="car", frame_idx=frame_idx,
                        ts_sec=frame_idx * 0.1, penetration=0.6)

    engine.finalize_missing(seen_track_ids=set())  # object leaves -- track_id 7 not in the set

    events = engine.get_closed_events()
    assert len(events) == 1
    assert events[0].track_id == 7
    assert events[0].confirmed is True


def test_video_ending_still_closes_active_confirmed_tracks():
    """If the video just ends while an object is still in the zone,
    finalize_all() should still close out any confirmed tracks."""
    engine = TemporalEngine()
    for frame_idx in range(config.CONSECUTIVE_FRAMES_THRESHOLD + 1):
        engine.observe(track_id=3, object_class="person", frame_idx=frame_idx,
                        ts_sec=frame_idx * 0.1, penetration=0.4)

    engine.finalize_all()  # video ended, no exit was ever seen

    assert len(engine.get_closed_events()) == 1