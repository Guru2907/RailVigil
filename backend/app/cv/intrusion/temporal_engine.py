"""
Temporal confirmation + ByteTrack ID-switch merging.

CONFIRM_DWELL_SEC / MISS_GRACE_SEC measured in video seconds.
ID switches: a new track_id can continue an existing event when it
overlaps an unobserved same-class-group track with IoU >= ID_MERGE_MIN_IOU.
"""

from app.core import config
from app.cv.common.zone_geometry import box_iou
from app.cv.intrusion.risk_engine import class_group


class TrackState:
    def __init__(self, track_id: int, object_class: str, frame_idx: int,
                 ts_sec: float, penetration: float, bbox=None):
        self.track_id = track_id
        self.object_class = object_class
        self.start_frame = frame_idx
        self.start_ts = ts_sec
        self.last_frame = frame_idx
        self.last_ts = ts_sec
        self.sightings = 1
        self.penetrations = [penetration]
        self.confirmed = False
        self.confirmed_ts = None
        self.snapshot_path = None
        self.last_bbox = bbox

    def update(self, frame_idx: int, ts_sec: float, penetration: float, bbox=None):
        self.last_frame = frame_idx
        self.last_ts = ts_sec
        self.sightings += 1
        self.penetrations.append(penetration)
        if bbox is not None:
            self.last_bbox = bbox

    def dwell_time(self) -> float:
        return max(0.0, self.last_ts - self.start_ts)

    def seconds_unseen(self, now_ts: float) -> float:
        return max(0.0, now_ts - self.last_ts)

    def max_penetration(self) -> float:
        return max(self.penetrations) if self.penetrations else 0.0

    def avg_penetration(self) -> float:
        return sum(self.penetrations) / len(self.penetrations) if self.penetrations else 0.0


class TemporalEngine:
    def __init__(self):
        self.active: dict[int, TrackState] = {}
        self.closed_events: list[TrackState] = []

    def _find_merge_candidate(self, object_class: str, bbox, frame_idx: int):
        if bbox is None:
            return None
        group = class_group(object_class)
        best_id, best_iou = None, config.ID_MERGE_MIN_IOU
        for tid, state in self.active.items():
            if state.last_frame == frame_idx:
                continue  # already observed this frame — never merge two concurrent objects
            if class_group(state.object_class) != group:
                continue
            if state.last_bbox is None:
                continue
            iou = box_iou(bbox, state.last_bbox)
            if iou >= best_iou:
                best_iou = iou
                best_id = tid
        return best_id

    def observe(self, track_id: int, object_class: str, frame_idx: int,
                ts_sec: float, penetration: float, bbox=None) -> TrackState:
        state = self.active.get(track_id)
        if state is None:
            merge_id = self._find_merge_candidate(object_class, bbox, frame_idx)
            if merge_id is not None:
                state = self.active.pop(merge_id)
                state.track_id = track_id
                self.active[track_id] = state
                state.update(frame_idx, ts_sec, penetration, bbox)
            else:
                state = TrackState(track_id, object_class, frame_idx, ts_sec, penetration, bbox)
                self.active[track_id] = state
        else:
            state.update(frame_idx, ts_sec, penetration, bbox)

        if not state.confirmed and state.dwell_time() >= config.CONFIRM_DWELL_SEC:
            state.confirmed = True
            state.confirmed_ts = ts_sec
        return state

    def finalize_missing(self, seen_track_ids: set[int], now_ts: float):
        for track_id in list(self.active.keys()):
            if track_id in seen_track_ids:
                continue
            state = self.active[track_id]
            if state.seconds_unseen(now_ts) > config.MISS_GRACE_SEC:
                self._close(track_id)

    def finalize_all(self):
        for track_id in list(self.active.keys()):
            self._close(track_id)

    def _close(self, track_id: int):
        state = self.active.pop(track_id)
        if state.confirmed:
            self.closed_events.append(state)

    def get_closed_events(self) -> list[TrackState]:
        return self.closed_events
