"""
Everything that happens to a SINGLE frame: run tracking, check each
tracked object against the zone, feed results into the temporal engine,
trigger a snapshot the moment something gets confirmed, and draw the
visual overlay (boxes + zone) onto the frame for the output video.

video_processor.py owns the loop over all frames; this file only knows
about one frame at a time.
"""

import cv2

from app.cv.tracker import Tracker
from app.cv.zone_engine import bbox_feet_point, point_in_zone, penetration_ratio
from app.cv.temporal_engine import TemporalEngine
from app.cv.snapshots import save_snapshot


class FrameProcessor:
    def __init__(self, tracker: Tracker, zone_poly, zmask, zone_label: str,
                 temporal_engine: TemporalEngine, video_id: str):
        self.tracker = tracker
        self.zone_poly = zone_poly
        self.zmask = zmask
        self.zone_label = zone_label
        self.temporal_engine = temporal_engine
        self.video_id = video_id

    def process(self, frame, frame_idx: int, ts_sec: float):
        """Runs tracking + zone/temporal logic on this frame, draws the
        overlay directly onto `frame`, and returns the annotated frame."""
        tracked = self.tracker.track(frame)
        seen_ids = set()

        for obj in tracked:
            feet = bbox_feet_point(obj["bbox"])
            inside = point_in_zone(feet, self.zone_poly)
            penetration = penetration_ratio(obj["bbox"], self.zmask) if inside else 0.0

            x1, y1, x2, y2 = [int(v) for v in obj["bbox"]]
            color = (0, 0, 255) if inside else (0, 200, 0)  # red if inside, green if not
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f'{obj["class_name"]} #{obj["track_id"]}', (x1, max(0, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            if not inside:
                continue

            seen_ids.add(obj["track_id"])
            state = self.temporal_engine.observe(
                track_id=obj["track_id"], object_class=obj["class_name"],
                frame_idx=frame_idx, ts_sec=ts_sec, penetration=penetration,
            )

            # Save exactly one snapshot per track -- the moment it FIRST
            # becomes confirmed, not every frame after that.
            if state.confirmed and state.snapshot_path is None:
                state.snapshot_path = save_snapshot(frame, self.video_id, obj["track_id"], ts_sec)

        # any track that was active but isn't in seen_ids this frame has left
        self.temporal_engine.finalize_missing(seen_ids)

        # draw the zone itself on top
        overlay = frame.copy()
        cv2.fillPoly(overlay, [self.zone_poly], (0, 255, 255))
        frame = cv2.addWeighted(overlay, 0.15, frame, 0.85, 0)
        cv2.polylines(frame, [self.zone_poly], isClosed=True, color=(0, 255, 255), thickness=2)
        cv2.putText(frame, self.zone_label, tuple(self.zone_poly[0]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        return frame