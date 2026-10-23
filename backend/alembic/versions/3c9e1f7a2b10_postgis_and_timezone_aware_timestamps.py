"""PostGIS extension and timezone-aware timestamps

Revision ID: 3c9e1f7a2b10
Revises: 66db0a636847
Create Date: 2026-10-22

PostgreSQL only; a no-op on SQLite, which has neither PostGIS nor a
timestamp-with-time-zone type.

Why the timestamp change: the models write timezone-aware UTC times. In a
`timestamp without time zone` column PostgreSQL would convert them to the
server's local zone (IST here) and drop the offset, so every stored time would
silently move by 5h30. `timestamptz` stores the instant correctly.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3c9e1f7a2b10"
down_revision: str | Sequence[str] | None = "66db0a636847"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIMESTAMP_COLUMNS = [
    ("users", "created_at"),
    ("videos", "created_at"),
    ("detections", "created_at"),
    ("incidents", "created_at"),
]


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _ensure_postgis() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")).scalar():
        return
    # Creating PostGIS needs a superuser; the app role normally is not one.
    if not bind.execute(sa.text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")).scalar():
        raise RuntimeError(
            "PostGIS is not enabled in this database. Run backend/scripts/setup_postgres.ps1, "
            "or connect as the postgres superuser and run: CREATE EXTENSION postgis;"
        )
    op.execute("CREATE EXTENSION postgis")


def upgrade() -> None:
    if not _is_postgres():
        return
    _ensure_postgis()
    for table, column in TIMESTAMP_COLUMNS:
        # Existing naive values were written as UTC, so read them as UTC.
        op.alter_column(
            table, column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=True,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    if not _is_postgres():
        return
    for table, column in TIMESTAMP_COLUMNS:
        op.alter_column(
            table, column,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
    # PostGIS is deliberately left installed: other database objects may use
    # it, and dropping an extension needs a superuser.
