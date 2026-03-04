"""add max stop sequence

Revision ID: 531bc22daafa
Revises: cddf5b4ac28f
Create Date: 2026-03-04 02:20:03.130792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '531bc22daafa'
down_revision: Union[str, Sequence[str], None] = 'cddf5b4ac28f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stop_events", sa.Column("max_stop_sequence", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("stop_events", "max_stop_sequence")
