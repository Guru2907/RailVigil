# Data model

## Today (PostgreSQL + PostGIS, or SQLite fallback; Alembic head `9944f93555d3`)
All `created_at` columns are timezone-aware (`timestamptz` on PostgreSQL) and stored as UTC.

- `videos` — one upload and its job state: `status` (`awaiting_zone` / queued / processing / done / failed), `progress`, `attempts`, `error`, `zone_json` (normalized points + source), `camera_label`, fps/size/duration, `output_video_path` (internal only; API exposes `has_output`).
- `incidents` — confirmed intrusion events per video (class, event type, severity, dwell, penetration, risk, snapshot path). Replaced as a whole when a video is re-run. **Do not add columns here for issue #3 part C.**
- `detections` — defined but never written; to be removed or used in v2.
- `users` — defined but unused until authentication.

### Encroachment (Phase 2a, `app/db/models/encroachment.py`)
Ids are full UUID hex strings. Locations are plain `latitude`/`longitude` columns (both databases); on PostgreSQL a GiST index on the point as geography (`ix_encroachment_sites_geog`) backs "within R metres" searches with PostGIS, and SQLite uses a bounding box plus haversine.

| Table | Key columns |
|---|---|
| `media` | one uploaded photo: status (queued / processing / done / failed), attempts, error, original filename, **sha256 (unique: the same file twice is one row)**, size, `captured_at` (EXIF, read as IST, stored UTC), `latitude`/`longitude` + `location_source` (exif / pin / none), zone, camera label, storage keys (original, annotated), model versions |
| `encroachment_findings` | one potential encroachment in a photo: class, model label, confidence, box, zone hit, overlap ratio and area, severity score and band, notes, model sources, crop key, `site_id` (null for photos without a location) |
| `encroachment_sites` | a place reported again and again: class, location, status, finding count, worst severity, first/last reported |
| `site_history` | every status change of a site (from → to, note, actor); site creation and automatic reopening included |
| `reports` | `report_no` (unique, `RV-ENC-YYYY-NNNNNN`), kind, reason (new_site / critical_finding / re_encroached), site, photo, finding |
| `report_counters` | last number per kind and year; incremented atomically inside the transaction that issues the report |

**Sites** (`services/site_service.py`): a finding joins the nearest site of the same class within `ENC_SITE_RADIUS_M` (25 m, provisional), else starts one. A **resolved** site found again is reopened as re-encroached; a **false_positive** site keeps its status (the finding is still attached). Workflow: `reported → under_review → verified → action_taken → resolved`, or `→ false_positive`; closed sites can be reopened to `reported`. Invalid moves are rejected (HTTP 409 once exposed by the API).

**Files** (`services/storage_service.py`): stored under `STORAGE_DIR` by key (`media/<id>/original.jpg`, `…/annotated.jpg`, `…/crops/NN.jpg`); only keys are in the database.

## Still planned
| Change | Phase |
|---|---|
| `locations` (named places / cameras with a saved right-of-way polygon) | later |
| `media` for videos too, replacing `videos` (one job model for photos and videos) | with issue #3 |
| `intrusion_events` replacing `incidents` (adds location, model version, report numbers `RV-INT-…`) | issue #3, part C |
| findings: segmentation mask, zone Z1/Z2, distance to rail in metres | Phases 4–5 |
| reports: PDF file, assignee | Future work |

**Report numbers:** `RV-ENC-YYYY-NNNNNN` and `RV-INT-YYYY-NNNNNN`, issued from the `report_counters` row inside the same transaction (atomic `UPDATE … RETURNING`), so they are unique under concurrent jobs.

**Media files are never stored in the database**, only their storage keys and checksums (see ADR-0002).
