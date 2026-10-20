"""Alembic environment: wires migrations to the app's models and database.

Two ways this runs:
  * from the app at startup  -> app.db.database.init_db() sets the URL
  * from the CLI (`alembic revision --autogenerate`, `alembic upgrade head`)
    -> the URL is empty in alembic.ini, so we fall back to config.DATABASE_URL

We deliberately do NOT call logging.config.fileConfig() (the Alembic
default). It would reset the app's logging setup every time the app starts.
"""

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.core import config as app_config
from app.db.database import Base

# Importing the models registers their tables on Base.metadata.
from app.db.models import detection, incident, user, video  # noqa: F401

alembic_config = context.config
if not alembic_config.get_main_option("sqlalchemy.url"):
    alembic_config.set_main_option("sqlalchemy.url", app_config.DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata

# SQLite can't ALTER most things in place. "Batch mode" makes Alembic
# rebuild the table instead (copy -> drop -> rename), so later migrations
# that change/drop columns work on SQLite too.
IS_SQLITE = alembic_config.get_main_option("sqlalchemy.url").startswith("sqlite")


def run_migrations_offline() -> None:
    context.configure(
        url=alembic_config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=IS_SQLITE,
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
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=IS_SQLITE,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
