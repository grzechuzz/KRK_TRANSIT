"""add weather schema

Revision ID: 58d205a207fd
Revises: a1b2c3d4e5f6
Create Date: 2026-03-30 17:40:13.377986

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58d205a207fd'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA weather")

    op.create_table(
        'hourly_observations',
        sa.Column('observed_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('temperature_c', sa.Double(), nullable=False),
        sa.Column('precipitation_mm', sa.Double(), nullable=False),
        sa.Column('rain_mm', sa.Double(), nullable=False),
        sa.Column('snowfall_cm', sa.Double(), nullable=False),
        sa.Column('snow_depth_cm', sa.Double(), nullable=False),
        sa.Column('wind_speed_kmh', sa.Double(), nullable=False),
        sa.Column('wind_gusts_kmh', sa.Double(), nullable=False),
        sa.Column('cloud_cover_pct', sa.SmallInteger(), nullable=False),
        sa.Column('visibility_m', sa.Double(), nullable=False),
        sa.Column('is_day', sa.Boolean(), nullable=False),
        sa.Column('weather_code', sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint('observed_at'),
        schema='weather',
    )

    op.execute("GRANT USAGE ON SCHEMA weather TO weather_collector")
    op.execute("GRANT SELECT, INSERT ON weather.hourly_observations TO weather_collector")


def downgrade() -> None:
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA weather FROM weather_collector")
    op.execute("REVOKE ALL ON SCHEMA weather FROM weather_collector")
    op.execute("DROP SCHEMA weather CASCADE")
