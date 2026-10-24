"""video camera location

Optional latitude/longitude per uploaded video (a map pin), so confirmed
intrusion incidents can be shown on the GIS map.

Revision ID: b7d2e4f1a903
Revises: 9944f93555d3
Create Date: 2026-10-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d2e4f1a903"
down_revision: str | Sequence[str] | None = "9944f93555d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("videos") as batch:
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("videos") as batch:
        batch.drop_column("longitude")
        batch.drop_column("latitude")
