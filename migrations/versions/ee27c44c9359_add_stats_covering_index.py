"""add stats covering index

Revision ID: ee27c44c9359
Revises: 58d205a207fd
Create Date: 2026-04-02 00:38:24.910523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee27c44c9359'
down_revision: Union[str, Sequence[str], None] = '58d205a207fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX idx_stop_events_stats_covering
        ON events.stop_events (line_number, service_date)
        INCLUDE (stop_sequence, max_stop_sequence, delay_seconds, trip_id, detection_method)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS events.idx_stop_events_stats_covering")
