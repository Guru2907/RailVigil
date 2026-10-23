# Intrusion module — specification

Owner: Siddeshwar. Code: `backend/app/cv/intrusion/`.

## Definition
An **intrusion** is a person, vehicle, or animal that enters a configured track-side safety zone and stays long enough to be confirmed.

## Pipeline
1. **Zone:** `ZoneResolver`. Missing zone → `ZoneUnavailable` (upload can park as `awaiting_zone`). Invalid zone → 422.
2. **Detection:** YOLOv8n + ByteTrack with `INTRUSION_CLASSES` (humans, vehicles, cow/dog/horse/sheep/elephant). Detector/Tracker default `class_filter=None`; intrusion workers pass the set explicitly.
3. **Confirmation:** `CONFIRM_DWELL_SEC` / `MISS_GRACE_SEC`. ID switches continue one event when IoU ≥ `ID_MERGE_MIN_IOU` (default 0.3), same class group, and the prior track was not seen this frame.
4. **Event types:** `human_intrusion` / `persistent_human_presence`, `vehicle_intrusion`, `animal_intrusion` / `persistent_animal_presence`, else `other_intrusion`.
5. **API:** `VideoOut` exposes `has_output` (bool), never `output_video_path`. `PUT /api/videos/{id}/zone` moves `awaiting_zone` → `queued`.

## Parameters (provisional)
See `backend/app/core/config.py`.
