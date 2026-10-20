# Intrusion module — specification

Owner: Siddeshwar. Code: `backend/app/cv/intrusion/`. This file describes what the code does today; update it in the same pull request as any behaviour change.

## Definition
An **intrusion** is a person or vehicle that enters a configured track-side safety zone in a video and stays there long enough to be confirmed. It is a transient event. It is never reported as encroachment.

## Pipeline (per video)
1. **Zone:** resolved by `ZoneResolver` (see [ZONES.md](ZONES.md)); the job fails with a clear message if no zone is available.
2. **Detection + tracking:** YOLOv8n (COCO weights) with ByteTrack via `Tracker`, run on every `FRAME_SAMPLE_INTERVAL`-th frame. Classes: `person, bicycle, car, motorcycle, bus, truck` (`RELEVANT_CLASSES`).
3. **Inside test:** an object is inside when the bottom-centre of its box (its ground-contact point) lies in the zone polygon. `penetration_ratio` = share of the box area inside the zone.
4. **Confirmation (`temporal_engine.py`):** a track becomes an event once it has been inside for `CONFIRM_DWELL_SEC` of video time. If it is unseen for up to `MISS_GRACE_SEC` the event continues; after that it closes. Unconfirmed tracks are dropped.
5. **Scoring (`risk_engine.py`):** `score = 100 × (w_pen × max_penetration + w_dwell × min(dwell / RISK_DWELL_NORM_SEC, 1)) × class_factor`; severity bands at 70 / 40 / 20 (critical / high / medium, else low). Rule-based, not learned.
6. **Event type:** `human_intrusion` or `persistent_human_presence` (person/bicycle, persistent when dwell ≥ `PERSISTENT_DWELL_THRESHOLD_SEC`), `vehicle_intrusion`, otherwise `other_intrusion`.
7. **Evidence:** one snapshot per event at the confirmation frame, plus an annotated H.264 video.

## Current parameters (all provisional)

| Setting | Value | Note |
|---|---|---|
| `CONF_THRESHOLD` | 0.35 | detector confidence cut-off |
| `FRAME_SAMPLE_INTERVAL` | 3 | detection on every 3rd frame |
| `CONFIRM_DWELL_SEC` | 0.6 s | the paper draft states 3 s; to be settled by evaluation |
| `MISS_GRACE_SEC` | 1.0 s | |
| `PERSISTENT_DWELL_THRESHOLD_SEC` | 8 s | demo value |
| Risk weights | 0.6 penetration / 0.4 dwell | class factors in `config.py` |

None of these values has been validated on labelled footage yet. Final values come from the evaluation in [EVALUATION.md](EVALUATION.md).

## Known limitations
- A tracker ID switch longer than the grace period splits one person into two events.
- Animals are not detected yet (planned: COCO cow, dog, horse, sheep, elephant as `animal_intrusion`).
- A fixed camera is assumed; the zone does not move with the camera.

## Planned
`awaiting_zone` job status with a "set zone" endpoint, automatic track zones, animal classes, ID-switch merging, a golden-clip regression test.
