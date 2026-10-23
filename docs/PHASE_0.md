# Phase 0 — PostgreSQL + PostGIS foundations (branch `feat/postgres`)

Status key: [x] done · [ ] to do

## Intrusion — remaining for Siddeshwar (track I)
- [ ] `awaiting_zone` status + set-zone endpoint
- [ ] Animal classes (cow, dog, horse, sheep, elephant)
- [ ] ID-switch merging
- [ ] Golden-clip regression test
- [ ] Stop returning `output_video_path`
- [ ] Rename `RELEVANT_CLASSES` → `INTRUSION_CLASSES`
- [ ] Move incidents into the v2 `intrusion_events` table (with Gurpreet, Phase 2)
- [ ] Intrusion evaluation set

The snapshot filename prefix (review item C4) is done by Gurpreet in Phase 1, because encroachment needs it.

## Phase 0 — main track (Gurpreet)

### Housekeeping
- [x] nvm-windows leftovers removed from user and machine PATH (backup: `C:\Users\Gurpreet\path-backup-2026-10-22.txt`)
- [ ] Delete the merged remote branch `stage-2/reliable-processing` (owner's OK first)

### Database setup
- [x] PostgreSQL 17 + PostGIS 3.6 installed (program on C:)
- [x] Setup script `backend/scripts/setup_postgres.ps1`: tablespace on E: (`E:\PostgresData\railvigil`), role `railvigil`, databases `railvigil` + `railvigil_test`, PostGIS in both, URLs written to `backend/.env` (never committed)
- [x] Run the setup script on this machine (asks for the postgres password)

### Code
- [x] `DateTime(timezone=True)` on all timestamps (fixes a silent 5h30 shift on PostgreSQL)
- [x] Migration `3c9e1f7a2b10`: `CREATE EXTENSION IF NOT EXISTS postgis` (PostgreSQL only) + timestamp type change
- [x] `pool_pre_ping` and a UTC session time zone for PostgreSQL in `backend/app/db/database.py`; PostGIS's `spatial_ref_sys` ignored by the startup guard and by Alembic
- [x] `tests/conftest.py` honours `TEST_DATABASE_URL`; `backend/scripts/test_postgres.ps1`
- [x] PostgreSQL migration tests: upgrade → check → downgrade → upgrade, PostGIS present, timestamps not shifted

### CI
- [x] Backend job on SQLite **and** a `backend-postgres` job (`postgis/postgis` service container on GitHub only)

### Docs
- [x] `docs/SETUP_POSTGRES.md` and the README setup section

### Done when
- [x] All tests pass on SQLite (118 passed, 2 PostgreSQL-only skipped)
- [x] All tests pass on PostgreSQL (120 passed, twice in a row)
- [x] `postgis_full_version()` works (PostGIS 3.6.2)
- [x] The server runs on PostgreSQL (both migrations applied on start-up)
- [x] A real clip produces incidents with correct timestamps (2 incidents; times returned in UTC, matching the upload moment)
