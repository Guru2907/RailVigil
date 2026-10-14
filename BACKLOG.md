# RailVigil — Backlog

Single place to track all planned work. Last updated: 2026-10-14.

## Working rules
- One branch per stage (`stage-N/<short-name>`). **No commit and no push unless the owner says so.**
- No Claude co-author trailer on commits/PRs.
- No extra features beyond this plan. Correctness and clean design first.
- Add code comments where logic is hard to follow (the *why*, not the *what*).
- Every task ends with tests or a manual check listed in its "Done when".

## Legend
- **Status:** `TODO` · `IN PROGRESS` · `DONE` · `BLOCKED` · `PARKED`
- **Size:** S (< half a day) · M (1–2 days) · L (3+ days)
- **Bug #:** refers to the numbered issue list from the codebase review (see "Bug index" at the bottom)

## Stage overview

| Stage | Goal | Status | Est. |
|---|---|---|---|
| 0 | Baseline and clip check | DONE (informal) | — |
| 1 | Correct encroachment logic | DONE (local branch; commit/push owner-controlled) | — |
| 2 | Reliable processing | **BUILT, uncommitted on `stage-2/reliable-processing`**; 100 tests pass; live-verified | 2–3 days |
| 3 | Auth and access control | TODO | 2–3 days |
| 4 | Incident review and data layer | TODO | 2 days |
| 5 | Evaluation | TODO (parallel from Stage 2) | 3–4 days |
| 6 | Structure and polish | TODO | 3–4 days |

---

## Stage 0: Baseline — DONE
- [x] 28 practice clips downloaded to `Desktop/railvigil-clips/` (outside repo; README.txt lists each)
- [x] Frame check on key clips. Usable: `person_walking_tracks_1`, `couple_walking_tracks`. Unusable for person detection (feet/legs only): `person_balancing_on_track`, `person_walking_tracks_winter`
- [x] Zone coordinate mapping verified: frontend sends pixel coords = normalized x frame width/height (`VideoAnalysis.jsx`), backend treats them as pixels

## Stage 1: Correct encroachment logic — DONE
Branch: `stage-1/core-encroachment-logic` · 28 backend tests pass.

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
- [ ] S1-X1 Proper false-alarm check: preset zone for `train_tracks_empty` sits below the train, so "no incidents" proves little. Use a zone overlapping the train. (feeds Stage 5)
- [ ] S1-X2 Preset zones in `scripts/run_clip.py` are rough; couple clip penetration is low (0.29–0.34). Widen presets ~15% per side. (S)
- [ ] S1-X3 `PERSISTENT_DWELL_THRESHOLD_SEC=8` is a demo value; every long walk becomes "persistent". Document, revisit in Stage 5
- [ ] S1-X4 Detection runs on every 3rd frame, so ID switches can still split events beyond the grace window (bug 7, mitigated not solved). Tune `FRAME_SAMPLE_INTERVAL` using Stage 5 numbers
- [ ] S1-X5 Optional later: `margin_px` safety margin around the drawn polygon (param already exists in `point_in_zone`, unused)

---

## Stage 2: Reliable processing — BUILT (awaiting owner review/commit)
Branch: `stage-2/reliable-processing` (created from `stage-1/core-encroachment-logic`; nothing committed or pushed).

### Status at a glance
| ID | Status | Notes |
|---|---|---|
| S2-01 logging | DONE | `core/logging.py` |
| S2-02 config | DONE | + `MAX_QUEUED_JOBS` (not in the original plan; back-pressure so uploads can't pile up) |
| S2-03 lifespan | DONE | `main.py` |
| S2-04 schema | DONE | D1 resolved: **Alembic pulled into Stage 2** (S4-03 is therefore done). One initial migration; a test fails if models and migrations drift |
| S2-05 zone validation | DONE | `utils/zone_validation.py` |
| S2-06 file validation | DONE | `utils/file_utils.py`, `utils/video_utils.py` |
| S2-07 non-blocking upload | DONE | route is a plain `def`, chunked streaming |
| S2-08 queue + workers | DONE | `services/job_queue.py`, `services/job_runner.py` |
| S2-09 startup recovery | DONE | `job_runner.recover_unfinished_jobs` |
| S2-10 error handling | DONE | catch-all is a middleware registered *before* CORS (verified: wrong order drops the CORS header on 500s) |
| S2-11 frontend minimum | DONE, **not built/linted** | `node_modules` not installed here; 3 small edits in `VideoAnalysis.jsx` / `Dashboard.jsx`. Run `npm run build` and look at the page |
| S2-12 tests | DONE | 100 backend tests, no model weights needed except the pre-existing end-to-end `test_video_processor.py` |

### Verified on a live server (real YOLO, real clips)
- 3 uploads back to back: accepted instantly, processed one at a time in order, progress advanced, model loaded once. Results identical to Stage 1 (1, 1 and 2 incidents). Same clip twice gave identical results.
- Hard kill (`Stop-Process -Force`) mid-job: row left as `processing` 18.9%; after restart it was requeued, ran as attempt 2 and finished `done`.

### Not verified live
- Graceful shutdown (Ctrl+C) mid-job. Covered by a unit test (job aborts, requeued, attempt refunded) but not exercised on a real server on Windows.
- Frontend changes (see S2-11).
- Upload of a very large file (the size cap is unit-tested with a tiny limit).

### Design changes vs. the plan above
- Recovery does **not** increment `attempts`; an attempt is counted when processing *starts*. A clean shutdown refunds its attempt.
- Completion is atomic: incidents are replaced and the video marked `done` in one transaction (re-running a video can no longer duplicate incidents).
- `process_video` now releases the video file/writer in a `finally` (it used to leak them on a crash) and accepts an injected tracker and an `abort_cb`.
- SQLite runs in WAL mode with a 5 s busy timeout, because the API and workers write to the same file.

### New follow-ups found while building (not done)
- [ ] S2-X1 `Video.output_video_path` (a server filesystem path) is still returned by the API. Frontend builds its own URL; stop exposing the path (S)
- [ ] S2-X2 A rotated phone video may report a different frame size to OpenCV than the browser shows, which would make zone validation reject a correct zone with a size-mismatch message. Test with a rotated clip (S)
- [ ] S2-X3 Videos with no frame count (some browser-recorded `.webm`) skip the `MAX_VIDEO_SEC` check (logged as a warning) (S)
- [ ] S2-X4 Run uvicorn with a single process only (documented in `job_queue.py` and `main.py`); several `--workers` would create independent queues
- [ ] S2-X5 `update_video_status` in `video_repository.py` is now unused; remove in Stage 6 cleanup

### Original plan (kept for reference)
**Goal:** uploads are validated, processed one at a time through a real queue with visible progress, failures are clean and never leak internals, and a restart never leaves a video stuck.

### Current problems (from the code)
- `video_service.start_video_processing` starts one raw daemon thread per upload: no limit, dies on restart, status stays `processing` forever (bugs 10, 11)
- `Tracker()` (loads YOLO) is created inside every `process_video` call (bug 11)
- `progress_cb` exists in `process_video` but `video_service` never passes it (bug 12)
- `upload_video` is `async def` but does blocking file read/write, freezing the server during uploads (bug 13)
- No file type/size check, whole file read into memory, `zone_points` JSON unchecked (bug 14)
- 500 handler returns `str(exc)`; failed videos store the full traceback in `Video.error`, which the API returns (bug 15)
- Unhandled-exception responses lack CORS headers, so the browser reports a CORS error instead of the real one (bug 16)
- `@app.on_event("startup")` is deprecated; `core/logging.py` is an empty stub (bug 19)

### Design (decisions made in this plan)
1. **In-process worker queue, DB is the source of truth.** `queue.Queue` of video ids + N worker threads (`WORKER_COUNT`, default 1). The `videos` table holds the real state, so a restart can rebuild the queue. Hidden behind a small `job_queue` module with `submit(video_id)` so swapping to RQ/Celery later only touches that module. Chosen because the deployment is one machine with SQLite; documented as a limitation.
2. **One model per worker, loaded once.** Each worker owns its own `Tracker`/`Detector`. A shared model across *concurrent* workers would mix ByteTrack state (`persist=True` keeps state on the model), so workers never share one. Between videos the tracker state is reset (`Tracker.reset()`), otherwise IDs from video A leak into video B. `process_video(..., tracker=None)` accepts an injected tracker (default keeps today's behaviour so existing tests still work).
3. **Status values:** `queued -> processing -> done | failed`. (`uploaded` retired; the frontend step map needs one small update, see S2-11.)
4. **Progress** stored on the video row as a 0–100 float, written at most every `PROGRESS_UPDATE_SEC` so we don't hammer SQLite.
5. **Recovery on startup:** `queued` -> re-enqueue; `processing` (orphaned by a crash/restart) -> back to `queued` and `attempts += 1`; once `attempts >= MAX_JOB_ATTEMPTS` mark `failed` with a clear message. The attempts cap stops a video that crashes the process (e.g. out-of-memory) from restarting forever.
6. **Upload endpoint becomes a plain `def`.** FastAPI runs sync endpoints in a threadpool, so blocking file I/O no longer stalls other requests. File is streamed to disk in chunks with a running size count (never fully in memory).
7. **Errors:** full traceback goes to the log only. The API and `Video.error` get a short, user-safe message (first line is what the frontend already shows). Unknown 500s return a generic message plus a request id for correlating with logs.

### Decision needed before S2-04
- **D1: schema changes (new `progress`, `attempts` columns).** The app uses `create_all`, which does not add columns to an existing `railvigil.db`.
  - **Option A (recommended):** pull Alembic setup forward from Stage 4 into this stage (S, ~half a day). Cleaner, and Stage 4 already needs it.
  - **Option B:** no migrations yet; delete the dev DB when schema changes. Fast, but fragile and it hides the problem until Stage 4.

### Tasks

| ID | Task | Files | Size | Bug # |
|---|---|---|---|---|
| S2-01 | Logging setup: implement `configure_logging()` (level from `LOG_LEVEL`, one format), call at startup, use `logging` everywhere in backend | `core/logging.py`, `main.py` | S | 19 |
| S2-02 | Config additions: `MAX_UPLOAD_MB`, `ALLOWED_VIDEO_EXTENSIONS`, `MAX_VIDEO_SEC`, `WORKER_COUNT`, `MAX_JOB_ATTEMPTS`, `PROGRESS_UPDATE_SEC`, `LOG_LEVEL`; mirror in `.env.example` | `core/config.py`, `.env.example` | S | — |
| S2-03 | Lifespan handler replacing `on_event("startup")`: create dirs, `init_db()`, start workers, run recovery; on shutdown stop workers gracefully (finish or requeue the current job) | `main.py` | S | 19 |
| S2-04 | Schema: add `progress`, `attempts`; status `queued`; also fill the already-existing `fps/width/height/duration_sec` columns from the uploaded file. Depends on **D1** | `db/models/video.py`, `db/schemas/video.py`, `video_repository.py`, (Alembic if D1=A) | S–M | 12 |
| S2-05 | Zone validation: pydantic model — list of >= 3 `[x, y]` numbers, max point count, inside the frame bounds (checked after reading frame size), non-zero area. Returns 422 with a clear message | `db/schemas/video.py` (or `schemas/zone.py`), `video_service.py` | S | 14 |
| S2-06 | File validation: extension whitelist, size cap while streaming (413), then open with OpenCV to confirm it is a readable video with frames and duration <= `MAX_VIDEO_SEC` (415/422). Delete the saved file if validation fails | `utils/file_utils.py`, `video_controller.py`, `routes/videos.py` | M | 14 |
| S2-07 | Non-blocking upload: `async def` -> `def`, chunked streaming write (`shutil.copyfileobj` or manual loop with size counter) | `routes/videos.py`, `file_utils.py` | S | 13 |
| S2-08 | Job queue + workers: `job_queue.py` (submit, worker loop, graceful stop), worker owns its `Tracker`; `Tracker.reset()`; `process_video(tracker=...)`; status transitions `queued -> processing -> done/failed`; progress callback throttled and written to DB | new `services/job_queue.py`, `video_service.py`, `cv/tracker.py`, `cv/video_processor.py` | M–L | 10, 11, 12 |
| S2-09 | Startup recovery: re-enqueue `queued`, requeue orphaned `processing` with `attempts += 1`, fail after `MAX_JOB_ATTEMPTS` with a clear message | `video_service.py` / `job_queue.py` | S | 10 |
| S2-10 | Error handling: generic handler logs traceback + returns generic message and request id; failed jobs store a short safe message (full traceback only in logs); fix CORS headers on 500s (handler or middleware ordered inside `CORSMiddleware`; add a test) | `middleware/error_handler.py`, `middleware/cors.py`, `video_service.py` | M | 15, 16 |
| S2-11 | Frontend minimum: map `queued` in the status-step order (`VideoAnalysis.jsx` ~lines 445–465, currently keyed on `uploaded`), show `progress` if present, show clean error text. No redesign (that is Stage 6) | `VideoAnalysis.jsx` | S | 12 |
| S2-12 | Tests (below) and manual runbook | `tests/` | M | — |

Suggested build order: S2-01 -> S2-02 -> S2-03 -> (D1) S2-04 -> S2-05/06/07 -> S2-08 -> S2-09 -> S2-10 -> S2-11 -> S2-12.

### Tests (S2-12)
Tests must run in CI **without YOLO weights**: monkeypatch `process_video`/`Tracker`, never download a model.
- `conftest.py`: set `DATABASE_URL`, `DATA_DIR`, `OUTPUTS_DIR` to a temp dir *before* importing the app (config reads env at import time); FastAPI `TestClient` (`httpx` already in requirements)
- Upload validation: bad extension -> 415, oversized -> 413, not a real video -> 422, zone with 2 points / out of bounds / zero area -> 422, valid upload -> 200 and file saved
- Queue: two uploads run in order with `WORKER_COUNT=1`; status goes `queued -> processing -> done`; progress writes are throttled
- Failure path: fake `process_video` raises -> status `failed`, `error` is short, contains no traceback/path
- Recovery: row stuck in `processing` at startup -> requeued, `attempts` incremented; at max attempts -> `failed`
- Error handler: unhandled exception returns generic body + request id, no exception text; response has CORS header
- Tracker reset: IDs/state do not carry over between two videos (unit-test the reset call with a fake model)
- Replace the placeholder tests in `tests/api/test_health.py` with a real health check

### Done when (Stage 2 acceptance)
1. Upload two videos back to back: they process in order, `progress` visibly advances, both finish
2. Upload a `.txt` renamed to `.mp4`, a huge file, and a bad zone: each returns a 4xx with a clear message, and no file is left behind
3. Kill the server mid-job, restart: the video is picked up again (or marked `failed` after the attempts cap), never stuck on `processing`
4. Force an error in the pipeline: API/`Video.error` show a short friendly message; the traceback appears only in the log
5. A 500 shows up in the browser as a normal error, not a CORS error
6. `pytest` passes with no network access and no model weights (the existing end-to-end `test_video_processor.py` is the one exception; marked as needing weights until Stage 6 fixes CI)
7. Re-run `scripts/run_clip.py` on `person_walking_tracks_1` and `couple_walking_tracks`: results unchanged from Stage 1 (1 and 2 incidents)

### Risks
- **Tracker state leaking between videos** is the subtle one. `persist=True` keeps ByteTrack state on the model, so a missed reset gives wrong IDs on the second upload. Covered by a test; also verify by uploading the same clip twice and comparing incidents.
- **Graceful shutdown on Windows with threads** can be fiddly. Keep workers as daemon threads *and* rely on startup recovery as the real safety net, so a hard kill is still correct.
- **SQLite and several writers.** Progress updates from workers plus API reads can hit "database is locked". Keep progress writes throttled; use short sessions per write.
- **In-process queue is single-process.** Running uvicorn with multiple workers would give each its own queue. Document: run with one process (known limitation).

### Out of scope for Stage 2
Cancelling or deleting jobs, retry button in the UI, RQ/Celery/Redis, auth (Stage 3), pagination (Stage 4), UI redesign (Stage 6).

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
- [ ] S6-04 Pin dependencies (`package.json` uses `latest`; `requirements.txt` unpinned); drop unused packages (`pandas`, `scipy`, `shapely`, `pydantic-settings`, `psycopg2-binary` if staying on SQLite) (bug 20) (S)
- [ ] S6-05 CI: cache deps, add lint (ruff + eslint), skip/mocked tests that need YOLO weights, split so torch is not installed for pure-API tests (S–M)
- [ ] S6-06 Docker Compose (backend, frontend, DB), README with architecture diagram + screenshots, short demo video (M)
- **Done when:** `docker compose up` runs the whole app, CI is green, README is current.

---

## Open decisions
| ID | Question | Needed by | Recommendation |
|---|---|---|---|
| D1 | Migrations: pull Alembic into Stage 2, or delete the dev DB on schema change? | S2-04 | **RESOLVED: Alembic pulled into Stage 2** (owner said to proceed; confirm if you disagree) |
| D2 | How do `<video>`/`<img>` tags authenticate once routes are protected (signed URLs vs blob fetch)? | S3-07 | Short-lived signed URLs |
| D3 | Keep the `Detection` table (store in-zone detections) or remove it? | S4-04 | Remove unless a replay/re-score view is built |
| D4 | Replay Studio (instant re-scoring on stored tracks): build or skip? | before Stage 4 | Skip; compute metrics with the Stage 5 script instead |

## Parked ideas (not in scope; only if everything above is done)
Time-to-clear vs train ETA · camera drift detection · trajectory intent · live RTSP monitoring · alerts (Telegram/email) · analytics heatmaps · Claude-written incident summaries · hotspot prediction.
Reason parked: the agreed scope is the core encroachment system done correctly, not extra features.

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
| 20 | Unpinned/unused dependencies | S6-04 |
| 21 | No authentication | S3-01 – S3-04 |
| 22 | CORS hard-coded | S3-05 |
| 23 | Auth stubs; `passlib`/`bcrypt` version trap | S3-01 |
| 24 | Placeholder pages, no routes/guard/404 | S3-06, S6-02 |
| 25 | `VideoAnalysis.jsx` too large | S6-01 |
| 26 | Polling without backoff, no auth token | S3-06, S6-01 |
