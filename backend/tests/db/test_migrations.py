"""Migrations and models must stay in sync. If you change a model and forget
`alembic revision --autogenerate`, `test_models_match_migrations` fails.

The PostgreSQL tests run only when the suite itself runs on PostgreSQL
(TEST_DATABASE_URL set, e.g. via scripts/test_postgres.ps1).
Each works in its own throwaway schema, so it never touches the tables the
rest of the suite uses."""

import os
import sqlite3
import uuid
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, make_url, text

from app.core import config
from app.db.database import ensure_migration_history

# conftest.py picks the suite's database before the app loads backend/.env;
# follow that choice, so plain `pytest` stays on SQLite.
PG_URL = os.environ.get("DATABASE_URL", "")
requires_postgres = pytest.mark.skipif(
    not PG_URL.startswith("postgresql"), reason="suite is not running on PostgreSQL (set TEST_DATABASE_URL)"
)


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(config.BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(config.BASE_DIR / "alembic"))
    # ConfigParser treats "%" as interpolation; URLs can contain %-escapes.
    cfg.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))
    return cfg


def test_upgrade_creates_all_tables(tmp_path):
    db_file = tmp_path / "fresh.db"
    command.upgrade(_alembic_config(f"sqlite:///{db_file.as_posix()}"), "head")

    tables = {r[0] for r in sqlite3.connect(db_file).execute("select name from sqlite_master where type='table'")}
    assert {"videos", "incidents", "detections", "users", "alembic_version"} <= tables


def test_video_has_job_columns(tmp_path):
    db_file = tmp_path / "fresh.db"
    command.upgrade(_alembic_config(f"sqlite:///{db_file.as_posix()}"), "head")

    cols = {r[1] for r in sqlite3.connect(db_file).execute("pragma table_info(videos)")}
    assert {"status", "progress", "attempts", "error"} <= cols


def test_models_match_migrations(tmp_path):
    db_file = tmp_path / "check.db"
    cfg = _alembic_config(f"sqlite:///{db_file.as_posix()}")
    command.upgrade(cfg, "head")
    command.check(cfg)          # raises if the models differ from the migrations


def test_downgrade_then_upgrade_round_trips(tmp_path):
    db_file = tmp_path / "round.db"
    cfg = _alembic_config(f"sqlite:///{db_file.as_posix()}")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


def test_existing_unversioned_database_is_not_reset(tmp_path):
    db_file = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE legacy_data (value TEXT)"))
        connection.execute(text("INSERT INTO legacy_data VALUES ('preserve me')"))

    with pytest.raises(RuntimeError, match="no Alembic migration history"):
        ensure_migration_history(engine)

    with engine.connect() as connection:
        assert connection.execute(text("SELECT value FROM legacy_data")).scalar_one() == "preserve me"
    engine.dispose()


def test_postgis_table_alone_does_not_trip_the_guard(tmp_path):
    """PostGIS creates spatial_ref_sys in a new database before any migration
    has run; that must not look like an unversioned app database."""
    engine = create_engine(f"sqlite:///{(tmp_path / 'postgis-like.db').as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE spatial_ref_sys (srid INTEGER)"))
    ensure_migration_history(engine)  # must not raise
    engine.dispose()


@pytest.fixture
def pg_schema_url():
    """URL for a fresh, empty schema in the PostgreSQL test database. The
    session time zone is set to IST on purpose, to catch timestamps that only
    look right when the server happens to run in UTC.

    The search path is ONLY the new schema. If `public` were on it, Alembic
    would find the suite's real `public.alembic_version`, and a downgrade here
    would drop the tables the other tests use. PostGIS functions live in
    `public`, so tests call them schema-qualified."""
    schema = f"migtest_{uuid.uuid4().hex[:10]}"
    admin = create_engine(PG_URL)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = make_url(PG_URL).update_query_dict(
        {"options": f"-csearch_path={schema} -cTimeZone=Asia/Kolkata"}
    )
    try:
        yield url.render_as_string(hide_password=False)
    finally:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@requires_postgres
def test_postgres_upgrade_check_and_round_trip(pg_schema_url):
    cfg = _alembic_config(pg_schema_url)
    command.upgrade(cfg, "head")
    command.check(cfg)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    # The downgrade must only have touched the throwaway schema.
    engine = create_engine(PG_URL)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT to_regclass('public.videos') IS NOT NULL")).scalar()
    finally:
        engine.dispose()


@requires_postgres
def test_postgres_has_postgis_and_timezone_aware_timestamps(pg_schema_url):
    command.upgrade(_alembic_config(pg_schema_url), "head")
    engine = create_engine(pg_schema_url)
    try:
        with engine.begin() as connection:
            assert connection.execute(text("SELECT public.postgis_lib_version()")).scalar()
            # The suite's own tables in `public` must be untouched by this schema's migrations.
            assert connection.execute(text("SELECT to_regclass('public.videos') IS NOT NULL")).scalar()
            col_type = connection.execute(text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = 'videos' AND column_name = 'created_at'"
            )).scalar_one()
            assert col_type == "timestamp with time zone"

            written = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
            connection.execute(
                text("INSERT INTO videos (id, filename, status, progress, attempts, created_at) "
                     "VALUES ('tz-check', 'x.mp4', 'queued', 0, 0, :ts)"),
                {"ts": written},
            )
            read_back = connection.execute(text("SELECT created_at FROM videos WHERE id = 'tz-check'")).scalar_one()
        assert read_back == written  # same instant, not shifted by the IST session
    finally:
        engine.dispose()
