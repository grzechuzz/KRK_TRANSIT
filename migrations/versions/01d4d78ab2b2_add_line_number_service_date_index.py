"""add line_number service_date index

Revision ID: 01d4d78ab2b2
Revises: 531bc22daafa
Create Date: 2026-03-11 16:33:13.792230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01d4d78ab2b2'
down_revision: Union[str, Sequence[str], None] = '531bc22daafa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX idx_stop_events_line_date
        ON stop_events (line_number, service_date)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_stop_events_line_date")
