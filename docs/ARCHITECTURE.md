# Architecture

## Today
```
React (Vite) ──HTTP──► FastAPI /api
                         ├─ POST /videos ─► validate upload + zone ─► Video row (queued) ─► job queue
                         │                                                  │ worker thread
                         │                       cv/intrusion/video_processor ◄┘
                         │                         Tracker (YOLOv8n + ByteTrack) → zone test
                         │                         → temporal confirmation → risk → snapshots
                         │                       incidents + video marked done (one transaction)
                         ├─ GET /videos, /videos/{id}, /videos/{id}/file
                         ├─ GET /incidents, /incidents/{id}, /incidents/{id}/snapshot
                         └─ GET /health
Storage: PostgreSQL + PostGIS (SQLite fallback) via SQLAlchemy + Alembic; files under backend/data/raw and backend/outputs
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
| 0 | Backend on native PostgreSQL + PostGIS (setup script, timezone-aware timestamps, CI on both databases). Docker and MinIO deferred to Phase 6 |
| 0b | Zone resolver extensions: `awaiting_zone`, zone suggestion endpoint, golden-clip tests |
| 1 | Encroachment baseline on images: pretrained models, manual zone, `classify_finding`, evidence |
| 2 | v2 schema, storage service, media/job API for images and videos, report numbers, site clustering |
| 3 | Frontend: Upload Center, Reports, GIS map, Dashboard for both modules |
| 4 (parallel from 1) | Dataset collection and labelling; fine-tuned encroachment and rail models |
| 5 | Automatic zones from rails; video keyframes for encroachment; animal intrusion |
| 6 | Authentication, PDF reports, notifications, deployment, paper update |

Data model: [DATA_MODEL.md](DATA_MODEL.md). Decisions: [decisions/](decisions/).
