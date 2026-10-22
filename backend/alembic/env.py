"""Alembic environment: wires migrations to the app's models and database.

Two ways this runs:
  * from the app at startup  -> app.db.database.init_db() sets the URL
  * from the CLI (`alembic revision --autogenerate`, `alembic upgrade head`)
    -> the URL is empty in alembic.ini, so we fall back to config.DATABASE_URL

We deliberately do NOT call logging.config.fileConfig() (the Alembic
default). It would reset the app's logging setup every time the app starts.
"""

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core import config as app_config
from app.db.database import EXTENSION_TABLES, Base, extension_owned_tables

# Importing the models registers their tables on Base.metadata.
from app.db.models import detection, encroachment, incident, user, video  # noqa: F401

alembic_config = context.config
if not alembic_config.get_main_option("sqlalchemy.url"):
    alembic_config.set_main_option("sqlalchemy.url", app_config.DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata

# SQLite can't ALTER most things in place. "Batch mode" makes Alembic
# rebuild the table instead (copy -> drop -> rename), so later migrations
# that change/drop columns work on SQLite too.
IS_SQLITE = alembic_config.get_main_option("sqlalchemy.url").startswith("sqlite")


# Indexes created by hand in migrations that the models cannot express
# (PostgreSQL-only functional indexes), so autogenerate must not drop them.
HAND_MADE_INDEXES = frozenset({"ix_encroachment_sites_geog"})


def make_include_object(skip_tables):
    """An include_object hook that leaves tables belonging to extensions
    (PostGIS and friends) and hand-made indexes out of autogenerate and
    `alembic check`, so they are never proposed for dropping."""
    def include_object(obj, name, type_, reflected, compare_to):
        if type_ == "table" and reflected and name in skip_tables:
            return False
        return not (type_ == "index" and reflected and name in HAND_MADE_INDEXES)
    return include_object


def run_migrations_offline() -> None:
    context.configure(
        url=alembic_config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=IS_SQLITE,
        include_object=make_include_object(EXTENSION_TABLES),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Ask the live database which tables its extensions own. The query
        # opens a transaction (SQLAlchemy autobegin); end it now, otherwise
        # Alembic would join it instead of starting and committing its own,
        # and the migration would be rolled back when the connection closes.
        skip_tables = extension_owned_tables(connection)
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=IS_SQLITE,
            include_object=make_include_object(skip_tables),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
