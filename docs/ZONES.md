# Zones

Both modules decide "is this on railway land / in the danger area" against a zone. All zones come from one place: `ZoneResolver` in `backend/app/cv/common/zones.py`.

## Rules
- No code builds a zone any other way.
- A missing zone is an error with a clear message (`ZoneUnavailable`). **The whole frame is never used as a fallback.**
- Zones are stored as **normalized** coordinates (0–1 of frame width/height) together with their **source**, so they work at any resolution and every result can say where its zone came from.

## Precedence (first one that exists wins)
1. **manual** — points sent with the upload (`zone_points`, pixel coordinates from the drawing canvas) or `--zone` on the CLI.
2. **sidecar** — a `zone_sidecar` JSON form field, or a `<video-stem>.zone.json` file next to the video (CLI).
3. **camera** — an entry for the upload's camera label in the `CAMERA_ZONES` environment variable.
4. **auto** — automatic zone from track detection. *Not implemented yet*; the provider returns nothing until a validated estimator is plugged in.

## Formats
Sidecar / camera record:

```json
{"format": "normalized", "points": [[0.10, 0.95], [0.90, 0.95], [0.55, 0.40], [0.45, 0.40]]}
```

`"format": "pixel"` with pixel points is also accepted. Older rows that stored `{"points": [...]}` in pixels are read as `source: "legacy"`.

Validation: at least 3 points, at most `MAX_ZONE_POINTS`, finite numbers, inside the frame, non-zero area.

## Deferred zone (`awaiting_zone`)
If no zone source is available at upload, the video is stored as `awaiting_zone` (not queued, not recovered, not counted toward queue limits). `PUT /api/videos/{id}/zone` validates points and queues processing. Invalid zones remain HTTP 422; missing zone at resolve time raises `ZoneUnavailable`.

## Planned
- **Encroachment zones:** Z1 track/fouling zone and Z2 railway corridor built around detected rails, plus Z3 operator-drawn right-of-way — see [ENCROACHMENT_SPEC.md](ENCROACHMENT_SPEC.md).
- `zone_mode` per upload (`manual` / `auto` / `hybrid`), a `POST /api/zones/suggest` endpoint.
- A confidence value on every resolved zone once automatic zones exist.
