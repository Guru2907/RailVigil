import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core import config
from app.cv.intrusion.temporal_engine import TemporalEngine

# Timing helpers so the tests read in terms of the rules, not magic numbers.
CONFIRM = config.CONFIRM_DWELL_SEC
GRACE = config.MISS_GRACE_SEC
STEP = 0.1  # seconds between "sampled frames" in these tests


def _observe_for(engine, track_id, start_ts, seconds, penetration=0.5, object_class="person"):
    """Feed one sighting every STEP seconds from start_ts for `seconds`.
    Returns the ts of the last sighting."""
    n = int(round(seconds / STEP)) + 1
    ts = start_ts
    for i in range(n):
        ts = start_ts + i * STEP
        engine.observe(track_id=track_id, object_class=object_class,
                       frame_idx=int(ts * 10), ts_sec=ts, penetration=penetration)
    return ts


def test_short_visit_is_not_confirmed():
    """Seen inside for less than CONFIRM_DWELL_SEC -> never confirmed,
    never becomes an incident."""
    engine = TemporalEngine()
    last = _observe_for(engine, 1, 0.0, CONFIRM - STEP)
    engine.finalize_missing(set(), now_ts=last + GRACE + 1.0)  # long gone
    assert engine.get_closed_events() == []


def test_single_sighting_can_never_confirm():
    """One sighting has dwell 0 regardless of the sample interval."""
    engine = TemporalEngine()
    state = engine.observe(track_id=1, object_class="person", frame_idx=0, ts_sec=0.0, penetration=0.9)
    assert state.confirmed is False


def test_long_visit_is_confirmed_and_closed_after_grace():
    engine = TemporalEngine()
    last = _observe_for(engine, 7, 0.0, CONFIRM + 0.5, object_class="car")

    # still inside the grace window -> stays open
    engine.finalize_missing(set(), now_ts=last + GRACE)
    assert engine.get_closed_events() == []
    assert 7 in engine.active

    # grace window exceeded -> closed as one event
    engine.finalize_missing(set(), now_ts=last + GRACE + STEP)
    events = engine.get_closed_events()
    assert len(events) == 1
    assert events[0].track_id == 7
    assert events[0].confirmed is True
    assert 7 not in engine.active


def test_brief_miss_does_not_split_one_intrusion():
    """The important one: a gap shorter than the grace window (one
    missed detection) must keep the SAME event going, and the dwell must
    span both halves."""
    engine = TemporalEngine()
    last = _observe_for(engine, 3, 0.0, CONFIRM + 1.0)

    # object missed for a while, but less than GRACE
    gap_end = last + GRACE * 0.5
    engine.finalize_missing(set(), now_ts=gap_end)

    # it's back
    last2 = _observe_for(engine, 3, gap_end, 1.0)
    engine.finalize_all()

    events = engine.get_closed_events()
    assert len(events) == 1
    assert events[0].dwell_time() == round(last2 - 0.0, 10)  # whole span, start to last sighting


def test_miss_longer_than_grace_makes_two_events():
    engine = TemporalEngine()
    last = _observe_for(engine, 3, 0.0, CONFIRM + 1.0)
    engine.finalize_missing(set(), now_ts=last + GRACE + 1.0)   # gone for good
    _observe_for(engine, 3, last + GRACE + 1.0, CONFIRM + 1.0)  # same id comes back later
    engine.finalize_all()
    assert len(engine.get_closed_events()) == 2


def test_grace_window_is_not_added_to_dwell():
    engine = TemporalEngine()
    last = _observe_for(engine, 5, 0.0, CONFIRM + 2.0)
    engine.finalize_missing(set(), now_ts=last + GRACE + STEP)
    (event,) = engine.get_closed_events()
    assert abs(event.dwell_time() - last) < 1e-9


def test_first_penetration_is_recorded():
    """Regression: the very first sighting used to be dropped from the
    penetration history, understating max/avg penetration."""
    engine = TemporalEngine()
    engine.observe(track_id=9, object_class="person", frame_idx=0, ts_sec=0.0, penetration=0.9)
    engine.observe(track_id=9, object_class="person", frame_idx=3, ts_sec=0.1, penetration=0.2)
    state = engine.active[9]
    assert state.max_penetration() == 0.9
    assert len(state.penetrations) == 2


def test_video_ending_still_closes_active_confirmed_tracks():
    """If the video just ends while an object is still in the zone,
    finalize_all() should still close out any confirmed tracks."""
    engine = TemporalEngine()
    _observe_for(engine, 3, 0.0, CONFIRM + 0.2)
    engine.finalize_all()  # video ended, no exit was ever seen
    assert len(engine.get_closed_events()) == 1
    assert engine.active == {}


def test_confirmed_ts_is_set_when_threshold_crossed():
    engine = TemporalEngine()
    last = _observe_for(engine, 2, 0.0, CONFIRM + 0.3)
    state = engine.active[2]
    assert state.confirmed_ts is not None
    assert CONFIRM <= state.confirmed_ts <= last
