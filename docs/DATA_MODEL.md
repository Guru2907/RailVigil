# Data model

## Today (SQLite, Alembic revision `66db0a636847`)
- `videos` — one upload and its job state: `status` (queued / processing / done / failed), `progress`, `attempts`, `error`, `zone_json` (normalized points + source), `camera_label`, fps/size/duration, `output_video_path`.
- `incidents` — confirmed intrusion events per video (class, event type, severity, dwell, penetration, risk, snapshot path). Replaced as a whole when a video is re-run.
- `detections` — defined but never written; to be removed or used in v2.
- `users` — defined but unused until authentication.

## Target (PostgreSQL + PostGIS) — planned
| Table | Key fields |
|---|---|
| `locations` | name, `geom` point, railway zone/division, station, km post, saved right-of-way polygon |
| `media` | kind (image/video), original/processed/thumbnail storage keys, sha256 (duplicate detection), size/fps/duration, `captured_at`, `geom`, `location_source` (exif / source / pin / camera), uploader, licence and source URL for public images |
| `jobs` | generalised from today's video job: status, progress, attempts, error |
| `encroachment_findings` | media id, frame time, class, confidence, mask polygon, box, zone hit (Z1/Z2/Z3/unknown), overlap m², distance to rail m, severity, evidence key, model version, site id |
| `encroachment_sites` | `geom`, dominant class, first/last reported, report count, status, assignee, notes |
| `intrusion_events` | today's incident fields plus class, `geom`, media id, model version |
| `reports` | `report_no`, type, linked site or event, status, PDF key, audit trail |
| `site_history` | status changes with who and when |

**Report numbers:** `RV-ENC-YYYY-NNNNNN` and `RV-INT-YYYY-NNNNNN`, issued from a database sequence so they are unique under concurrent jobs.

**Media files are never stored in the database**, only their storage keys and checksums (see ADR-0002).
