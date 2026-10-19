"""
This is the "does an object stay in the zone long enough to matter"
logic -- the state machine that turns a series of frame-by-frame
detections into a single confirmed event with a real dwell time.

Without this file: every frame where an object is in the zone would be
treated as a brand new isolated moment. With it: we track each object
(by its track_id) across the whole time it's in the zone, and only
"close" the event once it leaves -- so we know its true dwell time and
worst-case penetration, not just a single frame's snapshot.

Two timing rules live here, both measured in SECONDS of video time (not
frames, so they don't change with fps or the detection sample rate):

  * CONFIRM_DWELL_SEC  -- how long an object must be inside before it
                          becomes a real event (filters one-off flickers)
  * MISS_GRACE_SEC     -- how long an object may go unseen before its
                          event is closed (one missed detection must not
                          split a single intrusion into many incidents)

Lifecycle of one track:   new --> (dwell >= CONFIRM) --> confirmed
                          any state --> unseen > GRACE --> closed
Only CONFIRMED tracks become incidents when closed; the rest are dropped.
"""

from app.core import config


class TrackState:
    """Live bookkeeping for ONE tracked object, for as long as it's
    inside the zone. One of these exists per track_id, only while that
    object is actively being watched."""

    def __init__(self, track_id: int, object_class: str, frame_idx: int,
                 ts_sec: float, penetration: float):
        self.track_id = track_id
        self.object_class = object_class
        self.start_frame = frame_idx
        self.start_ts = ts_sec
        self.last_frame = frame_idx
        self.last_ts = ts_sec                  # last REAL sighting -- dwell is measured to here
        self.sightings = 1                     # how many sampled frames we've seen it inside
        self.penetrations = [penetration]      # one value per sighting, INCLUDING the first
        self.confirmed = False                 # True once dwell_time() >= CONFIRM_DWELL_SEC
        self.confirmed_ts = None               # video time at which it was confirmed
        self.snapshot_path = None              # filled in by frame_processor once confirmed

    def update(self, frame_idx: int, ts_sec: float, penetration: float):
        """Called every time this track_id is seen inside the zone again."""
        self.last_frame = frame_idx
        self.last_ts = ts_sec
        self.sightings += 1
        self.penetrations.append(penetration)

    def dwell_time(self) -> float:
        """Seconds between first and last REAL sighting inside the zone.
        Any grace window after the last sighting is deliberately not
        counted -- we don't know the object was there during it."""
        return max(0.0, self.last_ts - self.start_ts)

    def seconds_unseen(self, now_ts: float) -> float:
        return max(0.0, now_ts - self.last_ts)

    def max_penetration(self) -> float:
        return max(self.penetrations) if self.penetrations else 0.0

    def avg_penetration(self) -> float:
        return sum(self.penetrations) / len(self.penetrations) if self.penetrations else 0.0


class TemporalEngine:
    """Owns ALL currently-active TrackStates for one video. frame_processor
    calls this once per analysed frame with "who's inside the zone right
    now", and this class figures out who's new, who's continuing, and who
    has been gone long enough to be finalized into a closed event."""

    def __init__(self):
        self.active: dict[int, TrackState] = {}
        self.closed_events: list[TrackState] = []

    def observe(self, track_id: int, object_class: str, frame_idx: int,
                ts_sec: float, penetration: float) -> TrackState:
        """Call this for each object that IS inside the zone this frame."""
        state = self.active.get(track_id)
        if state is None:
            state = TrackState(track_id, object_class, frame_idx, ts_sec, penetration)
            self.active[track_id] = state
        else:
            state.update(frame_idx, ts_sec, penetration)

        # Confirmation is time-based: a single sighting has dwell 0 and can
        # never confirm, no matter what the sample interval is.
        if not state.confirmed and state.dwell_time() >= config.CONFIRM_DWELL_SEC:
            state.confirmed = True
            state.confirmed_ts = ts_sec

        return state

    def finalize_missing(self, seen_track_ids: set[int], now_ts: float):
        """Call once per analysed frame with the set of track_ids seen
        inside the zone THIS frame and the current video time. Tracks not
        in the set are left alone until they've been unseen for longer
        than MISS_GRACE_SEC -- then they're closed out. If the object is
        seen again inside the grace window, observe() simply continues
        the same TrackState and nothing is split."""
        for track_id in list(self.active.keys()):
            if track_id in seen_track_ids:
                continue
            state = self.active[track_id]
            if state.seconds_unseen(now_ts) > config.MISS_GRACE_SEC:
                self._close(track_id)

    def finalize_all(self):
        """Call once at the very end of the video -- anything still
        active (video ended while the object was still in the zone)
        gets closed out too."""
        for track_id in list(self.active.keys()):
            self._close(track_id)

    def _close(self, track_id: int):
        state = self.active.pop(track_id)
        # Unconfirmed tracks were just flickers -- drop them silently.
        if state.confirmed:
            self.closed_events.append(state)

    def get_closed_events(self) -> list[TrackState]:
        return self.closed_events
