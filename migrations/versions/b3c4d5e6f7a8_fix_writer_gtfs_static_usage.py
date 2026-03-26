"""fix writer missing USAGE on gtfs_static schema

Revision ID: b3c4d5e6f7a8
Revises: 4a8b9c2d3e1f
Create Date: 2026-03-26 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = '4a8b9c2d3e1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("GRANT USAGE ON SCHEMA gtfs_static TO writer")


def downgrade() -> None:
    op.execute("REVOKE USAGE ON SCHEMA gtfs_static FROM writer")
