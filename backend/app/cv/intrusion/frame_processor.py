"""
Everything that happens to a SINGLE frame, split into two steps:

  analyze(frame)  -- run tracking, check each object against the zone,
                     feed the results into the temporal engine. This is
                     the expensive part (YOLO), so video_processor only
                     calls it on every Nth frame.
  draw(frame)     -- paint the zone + boxes onto the frame. Cheap, so it
                     runs on EVERY frame; skipped frames reuse the last
                     analysed boxes. Without this the zone and boxes
                     would blink on and off in the output video.

process() ties the two together and, right after the overlay has been
drawn, saves the evidence snapshot for any track that was confirmed on
this frame -- so the snapshot shows the zone and every box, not a
half-drawn frame.

video_processor.py owns the loop over all frames; this file only knows
about one frame at a time.
"""

import cv2

from app.cv.common.snapshots import save_snapshot
from app.cv.common.tracker import Tracker
from app.cv.common.zone_geometry import bbox_feet_point, penetration_ratio, point_in_zone
from app.cv.intrusion.temporal_engine import TemporalEngine

# BGR colours (OpenCV order).
COLOR_INSIDE = (0, 0, 255)      # red: object is in the zone
COLOR_OUTSIDE = (0, 200, 0)     # green: object is outside
COLOR_ZONE = (0, 255, 255)      # yellow: the zone itself
ZONE_FILL_ALPHA = 0.15


class FrameProcessor:
    def __init__(self, tracker: Tracker, zone_poly, zmask, zone_label: str,
                 temporal_engine: TemporalEngine, video_id: str):
        self.tracker = tracker
        self.zone_poly = zone_poly
        self.zmask = zmask
        self.zone_label = zone_label
        self.temporal_engine = temporal_engine
        self.video_id = video_id
        # Boxes from the most recent analysed frame, redrawn on the frames
        # in between. At 25 fps with FRAME_SAMPLE_INTERVAL=3 they're at
        # most ~80 ms stale, which isn't noticeable at playback speed.
        self._last_tracked: list[dict] = []

    # ------------------------------------------------------------------
    # step 1: detection + tracking + zone/temporal logic (sampled frames)
    # ------------------------------------------------------------------
    def analyze(self, frame, frame_idx: int, ts_sec: float) -> list[dict]:
        """Returns the tracked objects for this frame. Each dict gets an
        extra `inside` flag and, if inside, a `state` (its TrackState)."""
        tracked = self.tracker.track(frame)
        seen_ids = set()

        for obj in tracked:
            # "Inside" is decided by the FEET point (bottom-centre of the
            # box) -- that's where the object touches the ground. The
            # box's centre could be up at head height, hanging over the
            # zone while the person is actually standing beside it.
            feet = bbox_feet_point(obj["bbox"])
            obj["inside"] = point_in_zone(feet, self.zone_poly)
            if not obj["inside"]:
                continue

            penetration = penetration_ratio(obj["bbox"], self.zmask)
            seen_ids.add(obj["track_id"])
            obj["state"] = self.temporal_engine.observe(
                track_id=obj["track_id"], object_class=obj["class_name"],
                frame_idx=frame_idx, ts_sec=ts_sec, penetration=penetration,
            )

        # Any active track NOT seen inside this frame starts (or continues)
        # its grace countdown; the engine closes it only once the grace
        # window has passed.
        self.temporal_engine.finalize_missing(seen_ids, now_ts=ts_sec)

        self._last_tracked = tracked
        return tracked

    # ------------------------------------------------------------------
    # step 2: overlay (every frame)
    # ------------------------------------------------------------------
    def draw(self, frame, tracked: list[dict]):
        """Draws the zone underneath, then the boxes on top, so box
        outlines stay crisp. Modifies and returns `frame`."""
        # translucent zone fill
        overlay = frame.copy()
        cv2.fillPoly(overlay, [self.zone_poly], COLOR_ZONE)
        frame = cv2.addWeighted(overlay, ZONE_FILL_ALPHA, frame, 1 - ZONE_FILL_ALPHA, 0)
        cv2.polylines(frame, [self.zone_poly], isClosed=True, color=COLOR_ZONE, thickness=2)
        cv2.putText(frame, self.zone_label, tuple(int(v) for v in self.zone_poly[0]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_ZONE, 2)

        for obj in tracked:
            x1, y1, x2, y2 = [int(v) for v in obj["bbox"]]
            color = COLOR_INSIDE if obj.get("inside") else COLOR_OUTSIDE
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f'{obj["class_name"]} #{obj["track_id"]}', (x1, max(0, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return frame

    # ------------------------------------------------------------------
    def process(self, frame, frame_idx: int, ts_sec: float, run_detection: bool):
        """One call per video frame. `run_detection` is True only on the
        sampled frames; the rest just get the overlay."""
        tracked = self.analyze(frame, frame_idx, ts_sec) if run_detection else self._last_tracked
        frame = self.draw(frame, tracked)

        if run_detection:
            # Exactly one snapshot per track: the first frame on which it
            # is confirmed. Taken AFTER draw() so the evidence image shows
            # the zone and all boxes. A track can only become confirmed
            # inside observe(), i.e. on a frame where it was seen, so the
            # just-confirmed object is always in `tracked` here.
            for obj in tracked:
                state = obj.get("state")
                if state is not None and state.confirmed and state.snapshot_path is None:
                    state.snapshot_path = save_snapshot(frame, self.video_id, obj["track_id"], ts_sec)

        return frame
