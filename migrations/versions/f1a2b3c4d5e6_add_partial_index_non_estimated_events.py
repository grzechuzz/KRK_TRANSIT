"""
Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-03-27 02:09:04.030120
"""

from typing import Sequence, Union

from alembic import op

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX idx_stop_events_line_date_non_estimated
        ON events.stop_events (line_number, service_date)
        WHERE detection_method = 1
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS events.idx_stop_events_line_date_non_estimated")
