# RailVigil Backend

FastAPI backend for railway intrusion detection: people, animals and vehicles entering configured track zones. Structures, vegetation and debris detection are out of scope.

Install from `backend/`: `pip install -r requirements.txt`
Run from `backend/`: `uvicorn app.main:app --reload`

Uploads normally include a manually drawn zone. Alternatively, submit a
`zone_sidecar` JSON form field or configure `CAMERA_ZONES` as a JSON object
mapping camera labels to normalized zone records. The CLI reads
`<video-stem>.zone.json` (or `<video-file>.zone.json`) when `--zone` is omitted.
Sidecars use `{"format":"normalized","points":[[0.1,0.2],[0.8,0.2],[0.8,0.9]]}`;
legacy pixel-point lists remain supported. Missing zones are rejected.
