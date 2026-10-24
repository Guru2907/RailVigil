# RailVigil — Backlog

> **Status (2026-10-24):**
> - **Current plan and phase status:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) ("Build order"). Phases 0–4 are done; Phase 5 is the final paper. Automatic zones, video keyframes, PDF reports, alerts, authentication and Docker are future work.
> - **Measured results:** [docs/EVALUATION.md](docs/EVALUATION.md).
> - **Open work:** tracked as GitHub issues.
> - The stage list below is the **historical** intrusion-only plan, kept for reference.

## Scope (read this first)

RailVigil has two separate modules (see `docs/decisions/ADR-0003-separate-modules.md`):

- **Physical encroachment** (main module, owner Gurpreet): structures, vegetation, debris and dumped material on or beside railway land, from images. In development — `docs/ENCROACHMENT_SPEC.md`.
- **Intrusion** (owner Siddeshwar): people and vehicles entering configured track-side safety zones in video. Stages 0–2 below are this module — `docs/INTRUSION_SPEC.md`.

Keep the terminology separate: intrusion events are never called encroachment and vice versa.

**v2 build order** (both modules, Postgres+PostGIS, GIS map, reports) is in `docs/ARCHITECTURE.md`. Stages 3–6 below are the earlier intrusion-only plan and will be merged into the v2 phases.

## Working rules
- One branch per stage (`stage-N/<short-name>`). **No commit and no push unless the owner says so.**
- No Claude co-author trailer on commits/PRs.
- No extra features beyond this plan. Correctness and clean design first.
- Add code comments where logic is hard to follow (the *why*, not the *what*).
- Every task ends with tests or a manual check listed in its "Done when".
- A missing or uncertain zone must **never** silently fall back to the whole frame. Fail clearly instead.

## Legend
- **Status:** `TODO` · `IN PROGRESS` · `DONE` · `BLOCKED` · `PARKED`
- **Size:** S (< half a day) · M (1–2 days) · L (3+ days)
- **Bug #:** refers to the numbered issue list from the codebase review (see "Bug index" at the bottom)

## Stage overview

| Stage | Goal | Status | Est. |
|---|---|---|---|
| 0 | Baseline and clip check | DONE (informal) | — |
| 1 | Correct intrusion / confirmation logic | DONE (local branch; commit/push owner-controlled) | — |
| 2 | Reliable processing + shared zone handling | **DONE on `stage-2/reliable-processing` (PR #1)**; review fixes applied | 2–3 days |
| 3 | Auth and access control | TODO | 2–3 days |
| 4 | Incident review and data layer | TODO | 2 days |
| 5 | Evaluation | TODO (parallel from Stage 2) | 3–4 days |
| 6 | Structure and polish | TODO | 3–4 days |

---

## Stage 0: Baseline — DONE
- [x] 28 practice clips downloaded to `Desktop/railvigil-clips/` (outside repo; README.txt lists each)
- [x] Frame check on key clips. Usable: `person_walking_tracks_1`, `couple_walking_tracks`. Unusable for person detection (feet/legs only): `person_balancing_on_track`, `person_walking_tracks_winter`
- [x] Zone coordinate mapping verified: frontend sends pixel coords = normalized x frame width/height (`VideoAnalysis.jsx`), backend treats them as pixels (stored records are now normalized with source metadata)

## Stage 1: Correct intrusion / confirmation logic — DONE
Branch: `stage-1/core-encroachment-logic` (historical branch name; scope is **intrusion**, not physical encroachment) · 28 backend tests pass.

- [x] S1-01 Confirmation measured in seconds (`CONFIRM_DWELL_SEC`) not sampled frames (bug 3)
- [x] S1-02 Grace period for missed detections (`MISS_GRACE_SEC`): one person = one incident (bug 2)
- [x] S1-03 Record first penetration value (bug 4)
- [x] S1-04 Draw zone and last boxes on every frame, no flicker (bug 1)
- [x] S1-05 Snapshot taken after full overlay is drawn (bug 6)
- [x] S1-06 Risk formula recalibrated (class scales the base), all severity bands reachable (bug 5)
- [x] S1-07 Dead event types tidied, bicycle = human, duplicate zone-mask removed, `print` -> logging (bugs 8, 9)
- [x] S1-08 `scripts/run_clip.py` + `lap` added to requirements
- [x] Verified: 1 person -> 1 incident, 2 people -> 2 incidents, overlay present on 60/60 frames

### Carried over from Stage 1 (not blocking)
- [ ] S1-X1 Proper false-alarm check: empty-track clip needs a zone that actually overlaps the train / distractors. (feeds Stage 5)
- [x] S1-X2 Filename-based `ZONE_PRESETS` and whole-frame fallback removed from `run_clip.py`. Use `--zone` or `.zone.json` sidecars (done in Stage 2 review)
- [ ] S1-X3 `PERSISTENT_DWELL_THRESHOLD_SEC=8` is provisional / demo-oriented; every long walk becomes "persistent". Document, revisit in Stage 5
- [ ] S1-X4 Detection runs on every 3rd frame, so ID switches can still split events beyond the grace window (bug 7, mitigated not solved). Tune `FRAME_SAMPLE_INTERVAL` using Stage 5 numbers
- [ ] S1-X5 Optional later: `margin_px` safety margin around the drawn polygon (param already exists in `point_in_zone`, unused)

---

## Stage 2: Reliable processing — DONE (PR #1 review addressed)
Branch: `stage-2/reliable-processing` · PR title should be: `feat(intrusion): reliable video processing and zone handling`

### Status at a glance
| ID | Status | Notes |
|---|---|---|
| S2-01 logging | DONE | `core/logging.py` |
| S2-02 config | DONE | + `MAX_QUEUED_JOBS`; thresholds marked provisional in comments |
| S2-03 lifespan | DONE | `main.py` |
| S2-04 schema | DONE | Alembic; models/migrations drift test |
| S2-05 zone validation | DONE | `utils/zone_validation.py` + shared `cv/common/zones.py` |
| S2-06 file validation | DONE | `utils/file_utils.py`, `utils/video_utils.py` |
| S2-07 non-blocking upload | DONE | route is a plain `def`, chunked streaming |
| S2-08 queue + workers | DONE | `services/job_queue.py`, `services/job_runner.py` |
| S2-09 startup recovery | DONE | `job_runner.recover_unfinished_jobs` |
| S2-10 error handling | DONE | catch-all middleware before CORS |
| S2-11 frontend minimum | DONE | queued status + progress; FormData via `globalThis` |
| S2-12 tests | DONE | migrations legacy-DB guard, zone resolver, upload paths, mark_done guard |
| S2-13 zone resolver | DONE | manual > sidecar > camera > auto; never whole-frame |
| S2-14 CV layout | DONE | shared in `cv/common/`, intrusion in `cv/intrusion/` |
| S2-15 deps | DONE | pinned (incl. `ultralytics==8.4.161`, `alembic>=1.16`) |
| S2-16 legacy DB | DONE | `ensure_migration_history()` refuses unversioned DBs; regression test |

### Zone handling (current)
- Shared `ZoneResolver` in `backend/app/cv/common/zones.py` with manual, sidecar, camera, and auto providers.
- Uploads, job processing, and `scripts/run_clip.py` all use the same resolution path.
- Zones are stored normalized with `format` + `source`; legacy pixel lists still load.
- Missing / uncertain zone → clear `ValidationFailed`, never full-frame fallback.

### Remaining zone / intrusion follow-ups (not blocking merge)
- [ ] S2-Z1 Ship `.zone.json` sidecars next to the three demo clips and re-check consistent incident counts via CLI
- [ ] S2-Z2 Optional auto-zone estimator (provider hook exists; no default estimator yet)
- [ ] S2-Z3 Camera zone admin UI / persistence (today: `CAMERA_ZONES` env JSON only)
- [ ] S2-X1 `Video.output_video_path` still returned by the API; stop exposing the server path (S)
- [ ] S2-X2 Rotated phone video may mismatch OpenCV vs browser frame size for zone validation (S)
- [ ] S2-X3 Videos with no frame count (some `.webm`) skip `MAX_VIDEO_SEC` (logged warning) (S)
- [ ] S2-X4 Run uvicorn with a single process only (documented); multi-`--workers` would fork queues
- [x] S2-X5 Removed unused `update_video_status`; `mark_done` requires `status == processing`

### Verified on a live server (real YOLO, real clips)
- 3 uploads back to back: accepted instantly, processed one at a time in order, progress advanced, model loaded once.
- Hard kill mid-job: row left as `processing`; after restart requeued and finished.

### Not verified live (owner checklist)
- Graceful shutdown (Ctrl+C) mid-job on Windows.
- Frontend: `npm run lint` and `npm run build` in `frontend/`.
- Attach `pytest -q` output from a fresh venv to the PR description.
- Rename PR title to the intrusion/video-processing wording above.

### Design notes
- Recovery does **not** increment `attempts` on clean shutdown; an attempt is counted when processing *starts*.
- Completion is atomic: incidents replaced and video marked `done` in one transaction.
- SQLite runs in WAL mode with a 5 s busy timeout.
- `classify_event_type()` never returns `persistent_encroachment`; unknown classes → `other_intrusion`.

### Original plan (kept for reference)
**Goal:** uploads are validated, processed one at a time through a real queue with visible progress, failures are clean and never leak internals, and a restart never leaves a video stuck.

### Current problems (from the code) — historical, fixed in this stage
- `video_service.start_video_processing` started one raw daemon thread per upload (bugs 10, 11) — fixed via queue
- `Tracker()` loaded inside every `process_video` call (bug 11) — fixed: one tracker per worker + reset
- No progress reporting (bug 12) — fixed
- Upload endpoint blocked the event loop (bug 13) — fixed
- No file/zone validation (bug 14) — fixed
- Errors leaked internals / CORS on 500s (bugs 15, 16) — fixed
- Deprecated `on_event`, empty logging stub (bug 19) — fixed

### Design (decisions made in this plan)
1. **In-process worker queue, DB is the source of truth.**
2. **One model per worker, loaded once.** `Tracker.reset()` between videos.
3. **Status values:** `queued -> processing -> done | failed`.
4. **Progress** on the video row, throttled by `PROGRESS_UPDATE_SEC`.
5. **Recovery on startup** with `MAX_JOB_ATTEMPTS` cap.
6. **Upload endpoint is a plain `def`** with chunked streaming.
7. **Errors:** traceback in logs only; short user-safe message in API / `Video.error`.

### Done when (Stage 2 acceptance)
1. Upload two videos back to back: they process in order, `progress` advances, both finish
2. Bad extension / huge file / bad zone: 4xx, no leftover file
3. Kill mid-job, restart: requeued or failed after attempts cap — never stuck on `processing`
4. Pipeline error: short friendly message; traceback only in logs
5. A 500 shows in the browser as a normal error, not a CORS error
6. `pytest` passes without network / weights (except the existing e2e processor test)
7. `run_clip.py` on demo clips with sidecar zones: consistent intrusion results (no whole-frame zone)

### Out of scope for Stage 2
Cancelling or deleting jobs, retry button in the UI, RQ/Celery/Redis, auth (Stage 3), pagination (Stage 4), UI redesign (Stage 6), **physical encroachment** (structures / vegetation / debris).

---

## Stage 3: Auth and access control — TODO
Branch: `stage-3/auth`
- [ ] S3-01 Password hashing + JWT create/verify (`core/security.py`). Pin compatible `passlib`/`bcrypt` versions (bug 23: newer `bcrypt` breaks `passlib`; or use `bcrypt` directly) (M)
- [ ] S3-02 User model/repository/service, `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` (M)
- [ ] S3-03 Roles `admin` / `operator` / `viewer` and a dependency that enforces them (S)
- [ ] S3-04 Protect all API routes **and** the `/static/outputs` mount (snapshots and annotated videos are currently public) (bug 21) (M)
- [ ] S3-05 Config-driven CORS origins (bug 22) (S)
- [ ] S3-06 Frontend: `AuthContext`, `useAuth`, route guard, login + signup pages, token on every request, token refresh/expiry handling, 404 page (bugs 24, 26) (M)
- [ ] S3-07 Videos/snapshots in `<video>`/`<img>` need auth: decide between short-lived signed URLs or fetching as blobs (**decision needed**)
- [ ] S3-08 Tests: signup/login, wrong password, expired token, role restrictions, unauthenticated access to every route returns 401
- **Done when:** nothing is reachable without logging in, roles restrict actions, refresh keeps you logged in.

## Stage 4: Incident review and data layer — TODO
Branch: `stage-4/incident-review`
- [ ] S4-01 Incident status `new / reviewed / false_alarm` + notes + reviewer + timestamp; API and UI (M)
- [ ] S4-02 Pagination (and sort) on `/incidents` and `/videos` (bug 18) (S)
- [x] S4-03 Alembic migrations: DONE in Stage 2 (D1). Remaining: write a migration for each schema change in this stage (bug 18)
- [ ] S4-04 Decide on the `Detection` table: write in-zone detections (needed if a replay/re-score view is built) or remove it (bug 18) (**decision needed**) (S)
- [ ] S4-05 Full-length UUID incident/video ids (8-char ids can collide) (bug 17) (S)
- [ ] S4-06 Tests for status workflow, pagination, migration up/down
- **Done when:** an operator can mark incidents from the UI and the change survives a migration.

## Stage 5: Evaluation — TODO (can run in parallel from Stage 2)
Branch: `stage-5/evaluation`
- [ ] S5-01 Label clips: CSV of `clip, start_sec, end_sec, class` per real intrusion (manual, any teammate)
- [ ] S5-02 Collect negatives: clips with nothing in the zone, plus a train overlapping the zone (carried from S1-X1)
- [ ] S5-03 Evaluation script: match predicted incidents to labels (time overlap), report recall, precision, false alarms per hour (M)
- [ ] S5-04 Use results to tune `CONFIRM_DWELL_SEC`, `MISS_GRACE_SEC`, `FRAME_SAMPLE_INTERVAL`, severity thresholds; record the final values and why
- [ ] S5-05 Put measured numbers in README (and an app page only if time allows)
- [ ] S5-06 Film 3–5 staged clips from a safe spot (nobody on a live line), fixed camera
- **Done when:** we have measured numbers we would be willing to put on a resume. Do not quote numbers that were not measured.

## Stage 6: Structure and polish — TODO
Branch: `stage-6/polish`
- [ ] S6-01 Split `VideoAnalysis.jsx` (645 lines) into components + `useVideoAnalysis` hook; polling backoff; error boundary (bugs 25, 26) (M)
- [ ] S6-02 Remove or finish placeholder pages and dead routes/links (bug 24) (S–M)
- [ ] S6-03 Remove pass-through layers and unused code; keep routes -> services -> repositories layering consistent (bug 9 follow-up) (M)
- [ ] S6-04 Drop unused packages if staying on SQLite (`pandas`, `scipy`, `shapely`, `pydantic-settings`, `psycopg2-binary`); keep pins current (bug 20) (S)
- [ ] S6-05 CI: cache deps, add lint (ruff + eslint), skip/mocked tests that need YOLO weights, split so torch is not installed for pure-API tests (S–M)
- [ ] S6-06 Docker Compose (backend, frontend, DB), README with architecture diagram + screenshots, short demo video (M)
- **Done when:** `docker compose up` runs the whole app, CI is green, README is current.

---

## Open decisions
| ID | Question | Needed by | Recommendation |
|---|---|---|---|
| D1 | Migrations: pull Alembic into Stage 2, or delete the dev DB on schema change? | S2-04 | **RESOLVED: Alembic pulled into Stage 2** |
| D2 | How do `<video>`/`<img>` tags authenticate once routes are protected (signed URLs vs blob fetch)? | S3-07 | Short-lived signed URLs |
| D3 | Keep the `Detection` table (store in-zone detections) or remove it? | S4-04 | Remove unless a replay/re-score view is built |
| D4 | Replay Studio (instant re-scoring on stored tracks): build or skip? | before Stage 4 | Skip; compute metrics with the Stage 5 script instead |

## Parked ideas (not in scope; only if everything above is done)
Time-to-clear vs train ETA · camera drift detection · trajectory intent · live RTSP monitoring · alerts (Telegram/email) · analytics heatmaps · Claude-written incident summaries · hotspot prediction.
Reason parked: the agreed scope is reliable **intrusion** detection done correctly, not extra features.

## Bug index
Numbers from the codebase review, mapped to where they are handled.

| Bug # | Issue | Handled in |
|---|---|---|
| 1 | Output video flicker | S1-04 DONE |
| 2 | One miss splits an incident | S1-02 DONE |
| 3 | Confirmation counted in sampled frames | S1-01 DONE |
| 4 | First penetration dropped | S1-03 DONE |
| 5 | Severity badly calibrated | S1-06 DONE |
| 6 | Snapshot taken mid-draw | S1-05 DONE |
| 7 | Detection at 1/3 frame rate, ID switches | mitigated by S1-02; tuning in S1-X4 / S5-04 |
| 8 | Dead event-type logic | S1-07 DONE |
| 9 | Duplicate zone-mask code | S1-07 DONE |
| 10 | Jobs stuck in `processing` after restart | S2-08, S2-09 |
| 11 | No queue/limit, model loaded per video | S2-08 |
| 12 | No progress reporting | S2-04, S2-08, S2-11 |
| 13 | Upload endpoint blocks the event loop | S2-07 |
| 14 | No upload/zone validation | S2-05, S2-06 |
| 15 | Errors leak internals | S2-10 |
| 16 | 500s show as CORS errors | S2-10 |
| 17 | 8-char ids can collide | S4-05 |
| 18 | `Detection` unused, no migrations, no pagination | S4-02, S4-03, S4-04 |
| 19 | Deprecated `on_event`, empty logging stub | S2-01, S2-03 |
| 20 | Unpinned/unused dependencies | S2-15 / S6-04 |
| 21 | No authentication | S3-01 – S3-04 |
| 22 | CORS hard-coded | S3-05 |
| 23 | Auth stubs; `passlib`/`bcrypt` version trap | S3-01 |
| 24 | Placeholder pages, no routes/guard/404 | S3-06, S6-02 |
| 25 | `VideoAnalysis.jsx` too large | S6-01 |
| 26 | Polling without backoff, no auth token | S3-06, S6-01 |
