"""reset db permissions to correct minimal privileges

Revision ID: e5f6a7b8c9d0
Revises: b3c4d5e6f7a8
Create Date: 2026-03-26 15:00:00.000000

Roles vs services:
  api_reader  -> API (reads gtfs_static + stop_events)
  rt_poller   -> RT Poller (reads current_stop_times only)
  writer      -> Stop Writer (reads gtfs_static via GtfsCache, inserts stop_events)
  importer    -> Importer (full access to gtfs_static for bulk GTFS loading)
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for year in range(2026, 2029):
        for month in range(1, 13):
            partition_name = f"stop_events_{year}_{month:02d}"
            op.execute(f"ALTER TABLE IF EXISTS public.{partition_name} SET SCHEMA events")

    for schema in ["public", "gtfs_static", "events"]:
        op.execute(
            f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema} FROM api_reader, rt_poller, writer, importer"
        )
        op.execute(
            f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA {schema} FROM api_reader, rt_poller, writer, importer"
        )
        op.execute(
            f"REVOKE ALL ON SCHEMA {schema} FROM api_reader, rt_poller, writer, importer"
        )

    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM api_reader"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM writer"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM importer"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM importer"
    )

    # api_reader: used by API service only
    op.execute("GRANT USAGE ON SCHEMA gtfs_static TO api_reader")
    op.execute("GRANT USAGE ON SCHEMA events TO api_reader")
    op.execute("GRANT SELECT ON gtfs_static.current_routes TO api_reader")
    op.execute("GRANT SELECT ON gtfs_static.current_trips TO api_reader")
    op.execute("GRANT SELECT ON gtfs_static.current_stop_times TO api_reader")
    op.execute("GRANT SELECT ON gtfs_static.current_shapes TO api_reader")
    op.execute("GRANT SELECT ON gtfs_static.current_stops TO api_reader")
    op.execute("GRANT SELECT ON events.stop_events TO api_reader")

    # rt_poller: used by RT Poller service
    # Reads current_stop_times to build stop_id -> stop_sequence maps for trip updates
    op.execute("GRANT USAGE ON SCHEMA gtfs_static TO rt_poller")
    op.execute("GRANT SELECT ON gtfs_static.current_stop_times TO rt_poller")

    # writer: used by Stop Writer
    # Needs SELECT on specific gtfs_static tables (via GtfsCache for event detection)
    # Needs INSERT, SELECT on stop_events
    op.execute("GRANT USAGE ON SCHEMA gtfs_static TO writer")
    op.execute("GRANT USAGE ON SCHEMA events TO writer")
    op.execute("GRANT SELECT ON gtfs_static.gtfs_meta TO writer")
    op.execute("GRANT SELECT ON gtfs_static.current_trips TO writer")
    op.execute("GRANT SELECT ON gtfs_static.current_stops TO writer")
    op.execute("GRANT SELECT ON gtfs_static.current_stop_times TO writer")
    op.execute("GRANT SELECT ON gtfs_static.current_routes TO writer")
    op.execute("GRANT SELECT, INSERT ON events.stop_events TO writer")

    # importer: used by Importer service
    # Full access to gtfs_static for bulk GTFS data loading (TRUNCATE + INSERT)
    # No access to events schema
    op.execute("GRANT USAGE ON SCHEMA gtfs_static TO importer")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA gtfs_static TO importer")
    op.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA gtfs_static TO importer")


def downgrade() -> None:
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA gtfs_static FROM api_reader, rt_poller, writer, importer")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA gtfs_static FROM importer")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA events FROM api_reader, writer")
    op.execute("REVOKE ALL ON SCHEMA gtfs_static FROM api_reader, rt_poller, writer, importer")
    op.execute("REVOKE ALL ON SCHEMA events FROM api_reader, writer")
