from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.common.constants import MIN_DELAY_SECONDS

_MAX_SEQ_EXPR = """COALESCE(e.max_stop_sequence, (
                        SELECT MAX(cst.stop_sequence)
                        FROM current_stop_times cst
                        WHERE cst.trip_id = e.trip_id
                    ))"""


class StatsRepository:
    def __init__(self, session: Session):
        self._session = session

    def max_delay_between_stops(self, line_number: str, start_date: date, end_date: date) -> list[dict[str, Any]]:
        """Generated delay = delay at stop N+1 - delay at stop N."""
        result = self._session.execute(
            text(f"""
                WITH filtered AS (
                    SELECT e.trip_id, e.service_date, e.stop_sequence, e.stop_name, e.headsign,
                        e.delay_seconds, e.line_number, e.license_plate, e.planned_time, e.event_time,
                        e.detection_method
                    FROM stop_events e
                    WHERE e.line_number = :line_number AND e.service_date BETWEEN :start_date AND :end_date
                    AND e.stop_sequence > 1
                    AND e.stop_sequence < {_MAX_SEQ_EXPR}
                ),
                consecutive AS (
                    SELECT trip_id, service_date, stop_sequence, stop_name, headsign, line_number,
                        license_plate, delay_seconds, planned_time, event_time, detection_method,
                        delay_seconds - LAG(delay_seconds) OVER w AS generated_delay,
                        LAG(delay_seconds) OVER w AS prev_delay,
                        LAG(stop_name) OVER w AS prev_stop_name,
                        LAG(stop_sequence) OVER w AS prev_stop_sequence,
                        LAG(planned_time) OVER w AS prev_planned_time,
                        LAG(event_time) OVER w AS prev_event_time,
                        LAG(license_plate) OVER w AS prev_license_plate,
                        LAG(detection_method) OVER w AS prev_detection_method
                    FROM filtered
                    WINDOW w AS (PARTITION BY trip_id, service_date ORDER BY stop_sequence)
                )
                SELECT trip_id, service_date, line_number, license_plate AS vehicle_number,
                    prev_stop_name AS from_stop, stop_name AS to_stop,
                    prev_stop_sequence AS from_sequence, stop_sequence AS to_sequence,
                    prev_planned_time AT TIME ZONE 'Europe/Warsaw' AS from_planned_time,
                    prev_event_time AT TIME ZONE 'Europe/Warsaw' AS from_event_time,
                    planned_time AT TIME ZONE 'Europe/Warsaw' AS to_planned_time,
                    event_time AT TIME ZONE 'Europe/Warsaw' AS to_event_time,
                    generated_delay AS delay_generated_seconds, headsign
                FROM consecutive
                WHERE generated_delay IS NOT NULL AND prev_delay >= :min_delay
                AND license_plate = prev_license_plate
                AND stop_sequence = prev_stop_sequence + 1
                AND detection_method != 2 AND prev_detection_method != 2
                ORDER BY generated_delay DESC
                LIMIT 10
            """),
            {
                "line_number": line_number,
                "start_date": start_date,
                "end_date": end_date,
                "min_delay": MIN_DELAY_SECONDS,
            },
        )
        return [dict(r) for r in result.mappings().all()]

    def trips_count(self, line_number: str, start_date: date, end_date: date) -> int:
        """Count distinct trips for a line in the given period."""
        result = self._session.execute(
            text("""
                SELECT COUNT(DISTINCT (trip_id, service_date)) FROM stop_events
                WHERE line_number = :line_number AND service_date BETWEEN :start_date AND :end_date
            """),
            {
                "line_number": line_number,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        return result.scalar() or 0

    def max_route_delay(self, line_number: str, start_date: date, end_date: date) -> list[dict[str, Any]]:
        """Route delay = delay at second-to-last stop - delay at second stop."""
        result = self._session.execute(
            text(f"""
                WITH filtered AS (
                    SELECT e.trip_id, e.service_date, e.stop_sequence, e.stop_name, e.headsign,
                        e.delay_seconds, e.line_number, e.license_plate, e.planned_time, e.event_time,
                        {_MAX_SEQ_EXPR} AS max_seq
                    FROM stop_events e
                    WHERE e.line_number = :line_number AND e.service_date BETWEEN :start_date AND :end_date
                    AND e.stop_sequence > 1
                    AND e.stop_sequence < {_MAX_SEQ_EXPR}
                ),
                trip_vehicle_check AS (
                    SELECT trip_id, service_date, COUNT(DISTINCT license_plate) AS vehicle_count
                    FROM filtered
                    GROUP BY trip_id, service_date
                ),
                boundary_check AS (
                    SELECT f.trip_id, f.service_date, f.max_seq,
                        bool_or(f.stop_sequence = 2) AS has_second,
                        bool_or(f.stop_sequence = f.max_seq - 1) AS has_penultimate
                    FROM filtered f
                    GROUP BY f.trip_id, f.service_date, f.max_seq
                ),
                valid_trips AS (
                    SELECT bc.trip_id, bc.service_date
                    FROM boundary_check bc
                    JOIN trip_vehicle_check tvc USING (trip_id, service_date)
                    WHERE bc.has_second AND bc.has_penultimate AND tvc.vehicle_count = 1
                ),
                trip_bounds AS (
                    SELECT f.trip_id, f.service_date, f.headsign, f.line_number, f.license_plate,
                        FIRST_VALUE(f.stop_name) OVER w AS first_stop,
                        LAST_VALUE(f.stop_name) OVER w_full AS last_stop,
                        (FIRST_VALUE(f.planned_time) OVER w) AT TIME ZONE 'Europe/Warsaw' AS first_planned_time,
                        (FIRST_VALUE(f.event_time) OVER w) AT TIME ZONE 'Europe/Warsaw' AS first_event_time,
                        (LAST_VALUE(f.planned_time) OVER w_full) AT TIME ZONE 'Europe/Warsaw' AS last_planned_time,
                        (LAST_VALUE(f.event_time) OVER w_full) AT TIME ZONE 'Europe/Warsaw' AS last_event_time,
                        FIRST_VALUE(f.delay_seconds) OVER w AS start_delay,
                        LAST_VALUE(f.delay_seconds) OVER w_full AS end_delay
                    FROM filtered f
                    JOIN valid_trips vt USING (trip_id, service_date)
                    WINDOW w AS (
                        PARTITION BY f.trip_id, f.service_date
                        ORDER BY f.stop_sequence
                    ),
                    w_full AS (
                        PARTITION BY f.trip_id, f.service_date
                        ORDER BY f.stop_sequence
                        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    )
                )
                SELECT * FROM (
                    SELECT DISTINCT ON (trip_id, service_date) trip_id, service_date, line_number,
                        license_plate AS vehicle_number, first_stop, last_stop,
                        first_planned_time, first_event_time, last_planned_time, last_event_time,
                        start_delay AS start_delay_seconds, end_delay AS end_delay_seconds,
                        (end_delay - start_delay) AS delay_generated_seconds, headsign
                    FROM trip_bounds
                    WHERE start_delay >= :min_delay
                    ORDER BY trip_id, service_date, delay_generated_seconds DESC
                ) ranked
                ORDER BY delay_generated_seconds DESC
                LIMIT 10
            """),
            {
                "line_number": line_number,
                "start_date": start_date,
                "end_date": end_date,
                "min_delay": MIN_DELAY_SECONDS,
            },
        )
        return [dict(r) for r in result.mappings().all()]

    def punctuality(self, line_number: str, start_date: date, end_date: date) -> dict[str, Any]:
        """
        For each stop in [2, n-1] range, classify individually:
        - on_time: delay <= 120s
        - slightly_delayed: 120s < delay <= 360s
        - delayed: delay > 360s

        Excludes estimated stops (detection_method=2)!!!
        """
        result = self._session.execute(
            text(f"""
                SELECT COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE e.delay_seconds <= 120) AS on_time,
                    COUNT(*) FILTER (WHERE e.delay_seconds > 120 AND e.delay_seconds <= 360) AS slightly_delayed,
                    COUNT(*) FILTER (WHERE e.delay_seconds > 360) AS delayed
                FROM stop_events e
                WHERE e.line_number = :line_number AND e.service_date BETWEEN :start_date AND :end_date
                AND e.stop_sequence > 1
                AND e.stop_sequence < {_MAX_SEQ_EXPR}
                AND e.delay_seconds >= :min_delay
                AND e.detection_method != 2
            """),
            {
                "line_number": line_number,
                "start_date": start_date,
                "end_date": end_date,
                "min_delay": MIN_DELAY_SECONDS,
            },
        )
        row = result.mappings().first()
        return dict(row) if row else {"total": 0, "on_time": 0, "slightly_delayed": 0, "delayed": 0}

    def trend(self, line_number: str, start_date: date, end_date: date) -> list[dict[str, Any]]:
        """Average delay per day for a line."""
        result = self._session.execute(
            text(f"""
                SELECT e.service_date AS "date",
                    ROUND(AVG(e.delay_seconds)::numeric, 1) AS avg_delay_seconds,
                    COUNT(DISTINCT (e.trip_id, e.service_date)) AS trips_count
                FROM stop_events e
                WHERE e.line_number = :line_number AND e.service_date BETWEEN :start_date AND :end_date
                AND e.stop_sequence > 1
                AND e.stop_sequence < {_MAX_SEQ_EXPR}
                AND e.delay_seconds >= :min_delay
                GROUP BY e.service_date
                ORDER BY e.service_date
            """),
            {
                "line_number": line_number,
                "start_date": start_date,
                "end_date": end_date,
                "min_delay": MIN_DELAY_SECONDS,
            },
        )
        return [dict(r) for r in result.mappings().all()]
