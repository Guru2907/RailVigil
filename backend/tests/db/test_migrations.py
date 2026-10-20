"""Migrations and models must stay in sync. If you change a model and forget
`alembic revision --autogenerate`, `test_models_match_migrations` fails."""

import sqlite3

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from app.core import config
from app.db.database import ensure_migration_history


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(config.BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(config.BASE_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
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
