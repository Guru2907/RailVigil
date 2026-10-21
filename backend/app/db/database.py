"""SQLAlchemy engine/session setup. PostgreSQL + PostGIS when DATABASE_URL
points at it (see docs/SETUP_POSTGRES.md); otherwise a local SQLite file,
which needs no server. Nothing else in the codebase depends on which."""

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core import config

IS_SQLITE = config.DATABASE_URL.startswith("sqlite")

# Tables that extensions create in our schema are not ours: the startup guard
# and Alembic's model comparison skip them. On PostgreSQL the database itself
# says which tables belong to an extension (extension_owned_tables); this
# constant is the fallback for SQLite and for Alembic's offline mode.
EXTENSION_TABLES = frozenset({"spatial_ref_sys"})

# Tables in the current schema that are members of an installed extension.
# Which extensions exist differs by machine: a plain PostGIS install adds only
# spatial_ref_sys, while the postgis/postgis Docker image used in CI also
# installs postgis_topology and postgis_tiger_geocoder.
_EXTENSION_TABLES_SQL = text("""
    SELECT c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    JOIN pg_depend d ON d.classid = 'pg_class'::regclass AND d.objid = c.oid AND d.deptype = 'e'
    WHERE n.nspname = current_schema() AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
""")


def extension_owned_tables(connection) -> set[str]:
    """Names of tables in the current schema that belong to extensions."""
    if connection.dialect.name != "postgresql":
        return set(EXTENSION_TABLES)
    return {row[0] for row in connection.execute(_EXTENSION_TABLES_SQL)} | set(EXTENSION_TABLES)

if IS_SQLITE:
    engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # pool_pre_ping replaces connections the server has closed (restart, idle
    # timeout) instead of failing the next request with them. The UTC session
    # time zone makes timestamps come back as +00:00 on every machine instead
    # of in the server's local zone (same instant either way).
    engine = create_engine(
        config.DATABASE_URL, pool_pre_ping=True, connect_args={"options": "-c timezone=UTC"}
    )
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


def ensure_migration_history(db_engine):
    """Refuse to migrate an existing unversioned database automatically."""
    with db_engine.connect() as connection:
        tables = set(inspect(connection).get_table_names()) - extension_owned_tables(connection)
    if tables and "alembic_version" not in tables:
        raise RuntimeError(
            "This database already contains tables but has no Alembic migration "
            "history (`alembic_version`). Startup stopped without changing it. "
            "Back up the database and migrate it explicitly; it will not be reset automatically. "
            f"Unexpected tables: {', '.join(sorted(tables))}"
        )


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
    ensure_migration_history(engine)
    command.upgrade(cfg, "head")
