"""SQLAlchemy engine/session setup. SQLite for local dev — one file, no
server needed. Swap DATABASE_URL in .env to a Postgres URL later;
nothing else in the codebase has to change."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core import config

IS_SQLITE = config.DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if IS_SQLITE else {}
engine = create_engine(config.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        """The API threads and the video workers write to the same SQLite
        file. By default a writer blocks readers and a second writer fails
        instantly with "database is locked". WAL lets readers and one
        writer work side by side, and busy_timeout makes a second writer
        wait (up to 5 s) instead of failing."""
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()


def get_db():
    """FastAPI dependency — yields a session, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Called once on app startup. Brings the database up to the latest
    schema by running Alembic migrations (alembic/versions/).

    Why not Base.metadata.create_all()? It only creates MISSING tables and
    never alters existing ones, so adding a column to a model would silently
    not reach an existing database. Migrations do, and they're versioned.

    To change the schema: edit the model, then from backend/ run
        alembic revision --autogenerate -m "describe the change"
    and review the generated file before committing it.
    """
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(config.BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(config.BASE_DIR / "alembic"))
    # ConfigParser treats "%" specially, so escape it (matters for URLs with
    # percent-encoded passwords).
    cfg.set_main_option("sqlalchemy.url", config.DATABASE_URL.replace("%", "%%"))
    command.upgrade(cfg, "head")