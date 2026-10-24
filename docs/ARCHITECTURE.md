# Architecture

## Today
```
React (Vite) ──HTTP──► FastAPI /api
  Intrusion (video)
   ├─ POST /videos ─► validate upload + zone ─► Video row (queued) ─► video job queue
   │                     cv/intrusion: YOLOv8n + ByteTrack → zone → temporal confirmation → risk
   │                     incidents + video done (one transaction)
   ├─ GET /videos, /videos/{id}, /videos/{id}/file
   └─ GET /incidents, /incidents/{id}, /incidents/{id}/snapshot
  Encroachment (photos)
   ├─ POST /media ─► check whole batch (type, size, image, zone, EXIF GPS / pin) ─► media rows (queued)
   │                  ─► photo job queue (second JobQueue instance)
   │                     cv/encroachment: Open Images V7 + YOLO-World → rule → evidence
   │                     findings + sites (PostGIS, 25 m) + reports + photo done (one transaction)
   ├─ GET /media, /media/{id}, /media/{id}/original, /media/{id}/annotated
   ├─ GET /encroachment/findings, /encroachment/findings/{id}/crop
   ├─ GET /encroachment/sites, /encroachment/sites/{id};  PATCH /encroachment/sites/{id}  (review workflow)
   ├─ GET /reports, /reports/{report_no}
   ├─ GET /map/features   (GeoJSON of sites)
   └─ GET /stats/summary  (both modules)
  GET /health
Storage: PostgreSQL + PostGIS (SQLite fallback) via SQLAlchemy + Alembic;
         video files under backend/data/raw and backend/outputs; photos and evidence under backend/storage
```

## Target (v2)
```
React: Upload Center · Dashboard (encroachment | intrusion) · GIS map of India · Reports · Sites
   │
FastAPI
   ├─ POST /media (images + videos, location, zone)       ─► job queue (images and videos)
   ├─ /encroachment/findings, /encroachment/sites          ─► cv/encroachment (YOLOv8-seg, zones Z1–Z3, rule)
   ├─ /intrusion/events                                    ─► cv/intrusion (existing pipeline)
   ├─ /reports, /reports/{report_no}, /reports/{report_no}/pdf
   ├─ /map/features (GeoJSON, server-side filters)
   └─ /stats/*
Shared: cv/common (detector, tracker, zone resolver, geometry), storage service, geo service
Storage: PostgreSQL + PostGIS (records) · object storage, local disk now / MinIO later (media files)
Deployment: Docker Compose (Postgres+PostGIS, MinIO, backend, frontend)
```

## Build order
| Phase | Deliverable |
|---|---|
| 0 | ✅ Backend on native PostgreSQL + PostGIS (setup script, timezone-aware timestamps, CI on both databases). Docker and MinIO are future work |
| 0b | Zone resolver extensions: `awaiting_zone`, zone suggestion endpoint, golden-clip tests |
| 1 | ✅ Encroachment baseline on images: pretrained models, manual zone, `classify_finding`, evidence |
| 2 | ✅ Encroachment data layer + photo API: media, findings, sites (PostGIS), reports, map GeoJSON, stats (videos unchanged; moving intrusion into the v2 model is issue #3) |
| 3 | ✅ Frontend: photo and video analysis, sites and reports, GIS map (clusters, heatmap, intrusion layer), dashboard for both modules |
| 4 | ✅ Dataset collection and labelling (217 Indian photos), fine-tuned encroachment model, measured evaluation ([EVALUATION.md](EVALUATION.md)) |
| 5 | Final paper: results, statistics, write-up |

**Future work** (not planned in the current build): automatic zones from detected rails; encroachment on video keyframes (which also verifies parked vehicles); PDF reports; alerts and notifications; authentication and roles; Docker deployment and MinIO object storage; `intrusion_events` with report numbers (issue #3 part C).

Data model: [DATA_MODEL.md](DATA_MODEL.md). Decisions: [decisions/](decisions/).
