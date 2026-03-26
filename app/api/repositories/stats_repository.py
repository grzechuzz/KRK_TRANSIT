from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.common.constants import ESTIMATED_VALID_FROM, MIN_DELAY_SECONDS

# When including estimated events, only trust them from the date cross-batch validation was deployed.
# STOPPED_AT events are always included regardless of date.
_ESTIMATED_FILTER = "AND (e.detection_method = 1 OR e.service_date >= :estimated_valid_from)"
_ESTIMATED_PREV_FILTER = (
    "AND (detection_method = 1 OR service_date >= :estimated_valid_from)"
    " AND (prev_detection_method = 1 OR service_date >= :estimated_valid_from)"
)


class StatsRepository:
    def __init__(self, session: Session):
        self._session = session

    def max_delay_between_stops(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> list[dict[str, Any]]:
        """Generated delay = delay at stop N+1 - delay at stop N."""
        det_filter = _ESTIMATED_FILTER if include_estimated else "AND e.detection_method = 1"
        prev_det_filter = (
            _ESTIMATED_PREV_FILTER if include_estimated else ("AND detection_method = 1 AND prev_detection_method = 1")
        )

        result = self._session.execute(
            text(f"""
                WITH filtered AS (
                    SELECT e.trip_id, e.service_date, e.stop_sequence, e.stop_name, e.headsign,
                        e.delay_seconds, e.line_number, e.license_plate, e.planned_time, e.event_time,
                        e.detection_method
                    FROM events.stop_events e
                    WHERE e.line_number = :line_number AND e.service_date BETWEEN :start_date AND :end_date
                    AND e.stop_sequence > 1
                    AND e.stop_sequence < e.max_stop_sequence
                    {det_filter}
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
                    generated_delay AS delay_generated_seconds, headsign,
                    (detection_method != 1 OR prev_detection_method != 1) AS is_estimated
                FROM consecutive
                WHERE generated_delay IS NOT NULL AND prev_delay >= :min_delay
                AND license_plate = prev_license_plate
                AND stop_sequence = prev_stop_sequence + 1
                {prev_det_filter}
                ORDER BY generated_delay DESC
                LIMIT 10
            """),
            {
                "line_number": line_number,
                "start_date": start_date,
                "end_date": end_date,
                "min_delay": MIN_DELAY_SECONDS,
                "estimated_valid_from": ESTIMATED_VALID_FROM,
            },
        )
        return [dict(r) for r in result.mappings().all()]

    def trips_count(self, line_number: str, start_date: date, end_date: date) -> int:
        """Count distinct trips for a line in the given period."""
        result = self._session.execute(
            text("""
                SELECT COUNT(DISTINCT (trip_id, service_date)) FROM events.stop_events
                WHERE line_number = :line_number AND service_date BETWEEN :start_date AND :end_date
            """),
            {
                "line_number": line_number,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        return result.scalar() or 0

    def max_route_delay(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> list[dict[str, Any]]:
        """Route delay = delay at second-to-last stop - delay at second stop."""
        det_filter = _ESTIMATED_FILTER if include_estimated else "AND e.detection_method = 1"

        result = self._session.execute(
            text(f"""
                WITH filtered AS (
                    SELECT e.trip_id, e.service_date, e.stop_sequence, e.stop_name, e.headsign,
                        e.delay_seconds, e.line_number, e.license_plate, e.planned_time, e.event_time,
                        e.max_stop_sequence, e.is_estimated
                    FROM events.stop_events e
                    WHERE e.line_number = :line_number AND e.service_date BETWEEN :start_date AND :end_date
                    AND e.stop_sequence > 1
                    AND e.stop_sequence < e.max_stop_sequence
                    {det_filter}
                ),
                trip_vehicle_check AS (
                    SELECT trip_id, service_date, COUNT(DISTINCT license_plate) AS vehicle_count
                    FROM filtered
                    GROUP BY trip_id, service_date
                ),
                boundary_check AS (
                    SELECT f.trip_id, f.service_date, f.max_stop_sequence,
                        bool_or(f.stop_sequence = 2) AS has_second,
                        bool_or(f.stop_sequence = f.max_stop_sequence - 1) AS has_penultimate
                    FROM filtered f
                    GROUP BY f.trip_id, f.service_date, f.max_stop_sequence
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
                        LAST_VALUE(f.delay_seconds) OVER w_full AS end_delay,
                        f.is_estimated
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
                        (end_delay - start_delay) AS delay_generated_seconds, headsign,
                        bool_or(is_estimated) OVER (PARTITION BY trip_id, service_date) AS is_estimated
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
                "estimated_valid_from": ESTIMATED_VALID_FROM,
            },
        )
        return [dict(r) for r in result.mappings().all()]

    def punctuality(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> dict[str, Any]:
        """
        For each stop in [2, n-1] range, classify individually:
        - on_time: delay <= 120s
        - slightly_delayed: 120s < delay <= 360s
        - delayed: delay > 360s
        """
        det_filter = _ESTIMATED_FILTER if include_estimated else "AND e.detection_method = 1"

        result = self._session.execute(
            text(f"""
                SELECT COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE e.delay_seconds <= 120) AS on_time,
                    COUNT(*) FILTER (WHERE e.delay_seconds > 120 AND e.delay_seconds <= 360) AS slightly_delayed,
                    COUNT(*) FILTER (WHERE e.delay_seconds > 360) AS delayed
                FROM events.stop_events e
                WHERE e.line_number = :line_number AND e.service_date BETWEEN :start_date AND :end_date
                AND e.stop_sequence > 1
                AND e.stop_sequence < e.max_stop_sequence
                AND e.delay_seconds >= :min_delay
                {det_filter}
            """),
            {
                "line_number": line_number,
                "start_date": start_date,
                "end_date": end_date,
                "min_delay": MIN_DELAY_SECONDS,
                "estimated_valid_from": ESTIMATED_VALID_FROM,
            },
        )
        row = result.mappings().first()
        return dict(row) if row else {"total": 0, "on_time": 0, "slightly_delayed": 0, "delayed": 0}

    def trend(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> list[dict[str, Any]]:
        """Average delay per day for a line."""
        det_filter = _ESTIMATED_FILTER if include_estimated else "AND e.detection_method = 1"

        result = self._session.execute(
            text(f"""
                SELECT e.service_date AS "date",
                    ROUND(AVG(e.delay_seconds)::numeric, 1) AS avg_delay_seconds,
                    COUNT(DISTINCT (e.trip_id, e.service_date)) AS trips_count
                FROM events.stop_events e
                WHERE e.line_number = :line_number AND e.service_date BETWEEN :start_date AND :end_date
                AND e.stop_sequence > 1
                AND e.stop_sequence < e.max_stop_sequence
                AND e.delay_seconds >= :min_delay
                {det_filter}
                GROUP BY e.service_date
                ORDER BY e.service_date
            """),
            {
                "line_number": line_number,
                "start_date": start_date,
                "end_date": end_date,
                "min_delay": MIN_DELAY_SECONDS,
                "estimated_valid_from": ESTIMATED_VALID_FROM,
            },
        )
        return [dict(r) for r in result.mappings().all()]
