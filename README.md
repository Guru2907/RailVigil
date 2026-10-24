# RailVigil

Railway right-of-way monitoring with YOLOv8, in two separate modules:

| Module | What it finds | Input | Status |
|---|---|---|---|
| **Physical encroachment** (main module) | Unauthorised structures, vegetation, debris and dumped material on or beside railway land | Images (and video keyframes) | **Working** (photo analysis, sites with review workflow, numbered reports, GIS map, dashboard). Pretrained models are the default; a fine-tuned model was trained and measured — see [docs/EVALUATION.md](docs/EVALUATION.md) and [docs/ENCROACHMENT_SPEC.md](docs/ENCROACHMENT_SPEC.md) |
| **Intrusion** | People and vehicles entering a track-side safety zone in video | Video | **Working** — see [docs/INTRUSION_SPEC.md](docs/INTRUSION_SPEC.md) |

Results are always *potential* encroachments or intrusions for an officer to review. Software cannot establish that something is illegal.

## What works today
- Upload a video with a safety zone (drawn, sidecar file, or per-camera config) → background job → YOLOv8n + ByteTrack → time-based confirmation → risk score → incidents with snapshots.
- Encroachment (API): upload photos (`POST /api/media`) with the railway land marked and an optional map pin → background job → pretrained YOLOv8 Open Images V7 + YOLO-World → findings with evidence → findings at the same place grouped into **sites** (PostGIS) → numbered **reports** (`RV-ENC-…`) → site review workflow, GeoJSON map layer and dashboard stats. Also as a command line: `backend/scripts/run_image.py`.
- Job queue with crash recovery, upload validation, PostgreSQL + PostGIS (SQLite fallback), Alembic migrations, ~300 backend tests.
- React pages: photo analysis, sites and reports, GIS map, dashboard for both modules, video analysis (upload + zone drawing), incidents.
- Dataset and training tools (`training/`): India-only collectors, pre-labelling, location-based splits, GPU training, evaluation.

## Not built yet
The final paper (Phase 5). Future work: automatic zones from detected rails, encroachment on video keyframes, PDF reports, alerts, authentication, Docker deployment, and intrusion events with report numbers. The plan is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); measured results are in [docs/EVALUATION.md](docs/EVALUATION.md).

## Run locally

Backend (from `backend/`):

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload     # one process only: the job queue is in-process
```

The YOLOv8n weights go in `backend/models/yolov8n.pt`.

Database: **PostgreSQL + PostGIS** — set it up once with [docs/SETUP_POSTGRES.md](docs/SETUP_POSTGRES.md) (`backend\scripts\setup_postgres.ps1` writes `DATABASE_URL` into `backend/.env`). Without `DATABASE_URL` the app falls back to a local SQLite file, `backend/railvigil.db`. Migrations run on start-up; a database that has tables but no migration history is refused with a message.

Frontend (from `frontend/`):

```bash
npm ci
npm run dev
```

Tests and checks: `pytest` (SQLite) and `scripts\test_postgres.ps1` (PostgreSQL) and `ruff check .` in `backend/`; `npm run lint` and `npm run build` in `frontend/`.

## Repository layout
- `backend/app/cv/common/` — detector, tracker, zone geometry and zone resolver shared by both modules
- `backend/app/cv/intrusion/` — intrusion pipeline
- `backend/app/cv/encroachment/` — encroachment pipeline (in development)
- `backend/app/services/` — upload handling, job queue and runner
- `frontend/` — React + Vite app
- `docs/` — specifications, data model, evaluation plan and decision records

## Team
Ownership and workflow: [CONTRIBUTING.md](CONTRIBUTING.md). Planned work: [BACKLOG.md](BACKLOG.md).
