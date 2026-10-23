# Intrusion module — specification

Owner: Siddeshwar. Code: `backend/app/cv/intrusion/`. This file describes what the code does today; update it in the same pull request as any behaviour change.

## Definition
An **intrusion** is a person, vehicle, or animal that enters a configured track-side safety zone in a video and stays there long enough to be confirmed. It is a transient event. It is never reported as encroachment.

## Pipeline (per video)
1. **Zone:** resolved by `ZoneResolver` (see [ZONES.md](ZONES.md)). Missing zone → `ZoneUnavailable` (upload can park as `awaiting_zone`). Invalid zone → 422. The whole frame is never used as a fallback.
2. **Detection + tracking:** YOLOv8n (COCO weights) with ByteTrack via `Tracker`, run on every `FRAME_SAMPLE_INTERVAL`-th frame. Classes: `INTRUSION_CLASSES` (person, bicycle, vehicles, cow/dog/horse/sheep/elephant). Detector/Tracker default `class_filter=None`; the intrusion pipeline passes the set explicitly.
3. **Inside test:** an object is inside when the bottom-centre of its box (its ground-contact point) lies in the zone polygon. `penetration_ratio` = share of the box area inside the zone.
4. **Confirmation (`temporal_engine.py`):** a track becomes an event once it has been inside for `CONFIRM_DWELL_SEC` of video time. If it is unseen for up to `MISS_GRACE_SEC` the event continues; after that it closes. Unconfirmed tracks are dropped. ID switches continue one event when IoU ≥ `ID_MERGE_MIN_IOU` (default 0.3), same class group, and the prior track was not seen this frame.
5. **Scoring (`risk_engine.py`):** `score = 100 × (w_pen × max_penetration + w_dwell × min(dwell / RISK_DWELL_NORM_SEC, 1)) × class_factor`; severity bands at 70 / 40 / 20 (critical / high / medium, else low). Rule-based, not learned.
6. **Event type:** `human_intrusion` / `persistent_human_presence`, `vehicle_intrusion`, `animal_intrusion` / `persistent_animal_presence`, otherwise `other_intrusion`.
7. **Evidence:** one snapshot per event at the confirmation frame, plus an annotated H.264 video.
8. **API:** `VideoOut` exposes `has_output` (bool), never `output_video_path`. `PUT /api/videos/{id}/zone` moves `awaiting_zone` → `queued`.

## Current parameters (candidates pending evaluation)

| Setting | Value | Note |
|---|---|---|
| `CONF_THRESHOLD` | 0.35 | detector confidence cut-off |
| `FRAME_SAMPLE_INTERVAL` | 3 | detection on every 3rd frame |
| `CONFIRM_DWELL_SEC` | 0.6 s | the paper draft states 3 s; to be settled by evaluation |
| `MISS_GRACE_SEC` | 1.0 s | |
| `ID_MERGE_MIN_IOU` | 0.3 | continue event after tracker ID switch |
| `PERSISTENT_DWELL_THRESHOLD_SEC` | 8 s | demo value |
| Risk weights | 0.6 penetration / 0.4 dwell | class factors in `config.py` |

None of these values has been validated on labelled footage yet. Final values come from the evaluation in [EVALUATION.md](EVALUATION.md).

## Known limitations
- A tracker ID switch with IoU below `ID_MERGE_MIN_IOU` (or different class group) can still split one object into two events.
- A fixed camera is assumed; the zone does not move with the camera.

## Related
Deferred zone upload flow: see [ZONES.md](ZONES.md). Regression / evaluation: issue #3.
