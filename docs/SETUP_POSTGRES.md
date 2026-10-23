# Local PostgreSQL + PostGIS (Windows, no Docker)

RailVigil runs on PostgreSQL with PostGIS (ADR-0001). SQLite still works with no setup when `DATABASE_URL` is not set, but map and site features will need PostgreSQL.

## 1. Install (once per machine)
1. `winget install PostgreSQL.PostgreSQL.17` (or the EDB installer). Choose a superuser (`postgres`) password, keep port **5432**, and tick **Stack Builder**.
2. Stack Builder → *PostgreSQL 17 on port 5432* → **Spatial Extensions → PostGIS 3.x Bundle**. In the PostGIS installer untick *Create spatial database*; answer **Yes** to `GDAL_DATA` / `PROJ_LIB` and **No** to raster drivers and out-db rasters.
3. Check: the Windows service `postgresql-x64-17` is *Running*.

## 2. Create RailVigil's databases
From the repository root, in your own terminal:

```powershell
powershell -ExecutionPolicy Bypass -File backend\scripts\setup_postgres.ps1
```

It asks for the `postgres` password (used only by the script, never stored) and then:
- creates the tablespace folder `E:\PostgresData\railvigil` so the project's data lives outside `C:\Program Files` (change with `-TablespaceDir D:\somewhere`; the folder must be empty and outside the git repository);
- creates the login role `railvigil` with a generated password, and the databases `railvigil` (app) and `railvigil_test` (tests) in that tablespace;
- enables PostGIS in both;
- writes `DATABASE_URL` and `TEST_DATABASE_URL` into `backend/.env` (git-ignored, values never printed) and checks that `railvigil` can log in.

Running it again is safe; it rotates the `railvigil` password and rewrites the two lines in `.env`.

Other options: `-PgBin` (PostgreSQL bin folder), `-Port`, `-ServiceName`.

## 3. Use it
- **App:** start the backend as usual (`uvicorn app.main:app` in `backend/`). It reads `DATABASE_URL` from `.env` and runs migrations on start-up.
- **Tests on PostgreSQL:** `powershell -ExecutionPolicy Bypass -File backend\scripts\test_postgres.ps1 -q`. Plain `pytest` still uses a throwaway SQLite file. CI runs both.
- **Back to SQLite:** remove or comment out `DATABASE_URL` in `backend/.env`.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `password authentication failed for user "postgres"` | Wrong superuser password; reset it with pgAdmin or reinstall. |
| `could not set permissions on directory` / `permission denied` when creating the tablespace | The service account (usually *Network Service*) needs full control of the folder; the script grants it — run it from an account that owns the folder. |
| Startup error *PostGIS is not enabled in this database* | Run the setup script again, or as `postgres`: `CREATE EXTENSION postgis;` in that database. |
| Startup error *database already contains tables but has no Alembic migration history* | The database was created outside migrations. Back it up, drop and recreate it with the setup script. |
| Times in the API end with `Z` | Expected: timestamps are stored with time zone and returned in UTC (`Z` = UTC). |
