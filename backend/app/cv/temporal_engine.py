"""
This is the "does an object stay in the zone long enough to matter"
logic -- the state machine that turns a series of frame-by-frame
detections into a single confirmed event with a real dwell time.

Without this file: every frame where an object is in the zone would be
treated as a brand new isolated moment. With it: we track each object
(by its track_id) across the whole time it's in the zone, and only
"close" the event once it leaves -- so we know its true dwell time and
worst-case penetration, not just a single frame's snapshot.
"""

from app.core import config


class TrackState:
    """Live bookkeeping for ONE tracked object, for as long as it's
    inside the zone. One of these exists per track_id, only while that
    object is actively being watched."""

    def __init__(self, track_id: int, object_class: str, frame_idx: int, ts_sec: float):
        self.track_id = track_id
        self.object_class = object_class
        self.start_frame = frame_idx
        self.start_ts = ts_sec
        self.last_frame = frame_idx
        self.last_ts = ts_sec
        self.consecutive_count = 1     # how many times in a row we've seen it inside the zone
        self.penetrations = []         # history of penetration_ratio values, one per sighting
        self.confirmed = False         # becomes True once consecutive_count crosses the threshold
        self.snapshot_path = None      # filled in by snapshots.py once confirmed

    def update(self, frame_idx: int, ts_sec: float, penetration: float):
        """Called every time this track_id is seen inside the zone again."""
        self.last_frame = frame_idx
        self.last_ts = ts_sec
        self.consecutive_count += 1
        self.penetrations.append(penetration)

    def dwell_time(self) -> float:
        return max(0.0, self.last_ts - self.start_ts)

    def max_penetration(self) -> float:
        return max(self.penetrations) if self.penetrations else 0.0

    def avg_penetration(self) -> float:
        return sum(self.penetrations) / len(self.penetrations) if self.penetrations else 0.0


class TemporalEngine:
    """Owns ALL currently-active TrackStates for one video. video_processor.py
    calls this once per frame with "who's inside the zone right now",
    and this class figures out who's new, who's continuing, and who
    just left (and should be finalized into a closed event)."""

    def __init__(self):
        self.active: dict[int, TrackState] = {}
        self.closed_events: list[TrackState] = []

    def observe(self, track_id: int, object_class: str, frame_idx: int, ts_sec: float, penetration: float):
        """Call this for each object that IS inside the zone this frame."""
        state = self.active.get(track_id)
        if state is None:
            state = TrackState(track_id, object_class, frame_idx, ts_sec)
            self.active[track_id] = state
        else:
            state.update(frame_idx, ts_sec, penetration)

        if not state.confirmed and state.consecutive_count >= config.CONSECUTIVE_FRAMES_THRESHOLD:
            state.confirmed = True

        return state

    def finalize_missing(self, seen_track_ids: set[int]):
        """Call this once per frame with the set of track_ids seen
        inside the zone THIS frame. Any track that was active before but
        isn't in that set anymore has left the zone -- close it out."""
        for track_id in list(self.active.keys()):
            if track_id not in seen_track_ids:
                state = self.active.pop(track_id)
                if state.confirmed:
                    self.closed_events.append(state)

    def finalize_all(self):
        """Call once at the very end of the video -- anything still
        active (video ended while the object was still in the zone)
        gets closed out too."""
        for track_id in list(self.active.keys()):
            state = self.active.pop(track_id)
            if state.confirmed:
                self.closed_events.append(state)

    def get_closed_events(self) -> list[TrackState]:
        return self.closed_events