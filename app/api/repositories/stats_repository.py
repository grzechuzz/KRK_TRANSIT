from datetime import date
from typing import Any

import sqlalchemy as sa
from sqlalchemy import and_, distinct, func, or_
from sqlalchemy.orm import Session

from app.common.constants import ESTIMATED_VALID_FROM, MIN_DELAY_SECONDS, TIMEZONE

_TZ = TIMEZONE

# Lightweight Core table descriptor — used only for query building, not DDL or reflection.
_stop_events = sa.Table(
    "stop_events",
    sa.MetaData(),
    sa.Column("trip_id"),
    sa.Column("service_date"),
    sa.Column("stop_sequence"),
    sa.Column("stop_name"),
    sa.Column("headsign"),
    sa.Column("delay_seconds"),
    sa.Column("line_number"),
    sa.Column("license_plate"),
    sa.Column("planned_time"),
    sa.Column("event_time"),
    sa.Column("detection_method"),
    sa.Column("max_stop_sequence"),
    sa.Column("is_estimated"),
    schema="events",
)


def _det_filter(tbl: Any, include_estimated: bool) -> Any:
    """WHERE condition for detection_method. Values come from internal constants only."""
    if include_estimated:
        return or_(tbl.c.detection_method == 1, tbl.c.service_date >= ESTIMATED_VALID_FROM)
    return tbl.c.detection_method == 1


def _prev_det_filter(tbl: Any, include_estimated: bool) -> Any:
    """WHERE condition for both current and previous detection_method (consecutive CTE)."""
    if include_estimated:
        return and_(
            or_(tbl.c.detection_method == 1, tbl.c.service_date >= ESTIMATED_VALID_FROM),
            or_(tbl.c.prev_detection_method == 1, tbl.c.service_date >= ESTIMATED_VALID_FROM),
        )
    return and_(tbl.c.detection_method == 1, tbl.c.prev_detection_method == 1)


class StatsRepository:
    def __init__(self, session: Session):
        self._session = session

    def max_delay_between_stops(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> list[dict[str, Any]]:
        """Generated delay = delay at stop N+1 - delay at stop N."""
        e = _stop_events.alias("e")

        filtered = (
            sa.select(
                e.c.trip_id,
                e.c.service_date,
                e.c.stop_sequence,
                e.c.stop_name,
                e.c.headsign,
                e.c.delay_seconds,
                e.c.line_number,
                e.c.license_plate,
                e.c.planned_time,
                e.c.event_time,
                e.c.detection_method,
            )
            .where(
                and_(
                    e.c.line_number == line_number,
                    e.c.service_date.between(start_date, end_date),
                    e.c.stop_sequence > 1,
                    e.c.stop_sequence < e.c.max_stop_sequence,
                    _det_filter(e, include_estimated),
                )
            )
            .cte("filtered")
        )

        part_by = [filtered.c.trip_id, filtered.c.service_date]
        order_by = filtered.c.stop_sequence

        consecutive = sa.select(
            filtered.c.trip_id,
            filtered.c.service_date,
            filtered.c.stop_sequence,
            filtered.c.stop_name,
            filtered.c.headsign,
            filtered.c.line_number,
            filtered.c.license_plate,
            filtered.c.delay_seconds,
            filtered.c.planned_time,
            filtered.c.event_time,
            filtered.c.detection_method,
            (
                filtered.c.delay_seconds
                - func.lag(filtered.c.delay_seconds).over(partition_by=part_by, order_by=order_by)
            ).label("generated_delay"),
            func.lag(filtered.c.delay_seconds).over(partition_by=part_by, order_by=order_by).label("prev_delay"),
            func.lag(filtered.c.stop_name).over(partition_by=part_by, order_by=order_by).label("prev_stop_name"),
            func.lag(filtered.c.stop_sequence)
            .over(partition_by=part_by, order_by=order_by)
            .label("prev_stop_sequence"),
            func.lag(filtered.c.planned_time).over(partition_by=part_by, order_by=order_by).label("prev_planned_time"),
            func.lag(filtered.c.event_time).over(partition_by=part_by, order_by=order_by).label("prev_event_time"),
            func.lag(filtered.c.license_plate)
            .over(partition_by=part_by, order_by=order_by)
            .label("prev_license_plate"),
            func.lag(filtered.c.detection_method)
            .over(partition_by=part_by, order_by=order_by)
            .label("prev_detection_method"),
        ).cte("consecutive")

        q = (
            sa.select(
                consecutive.c.trip_id,
                consecutive.c.service_date,
                consecutive.c.line_number,
                consecutive.c.license_plate.label("vehicle_number"),
                consecutive.c.prev_stop_name.label("from_stop"),
                consecutive.c.stop_name.label("to_stop"),
                consecutive.c.prev_stop_sequence.label("from_sequence"),
                consecutive.c.stop_sequence.label("to_sequence"),
                func.timezone(_TZ, consecutive.c.prev_planned_time).label("from_planned_time"),
                func.timezone(_TZ, consecutive.c.prev_event_time).label("from_event_time"),
                func.timezone(_TZ, consecutive.c.planned_time).label("to_planned_time"),
                func.timezone(_TZ, consecutive.c.event_time).label("to_event_time"),
                consecutive.c.generated_delay.label("delay_generated_seconds"),
                consecutive.c.headsign,
                or_(
                    consecutive.c.detection_method != 1,
                    consecutive.c.prev_detection_method != 1,
                ).label("is_estimated"),
            )
            .where(
                and_(
                    consecutive.c.generated_delay.isnot(None),
                    consecutive.c.prev_delay >= MIN_DELAY_SECONDS,
                    consecutive.c.license_plate == consecutive.c.prev_license_plate,
                    consecutive.c.stop_sequence == consecutive.c.prev_stop_sequence + 1,
                    _prev_det_filter(consecutive, include_estimated),
                )
            )
            .order_by(consecutive.c.generated_delay.desc())
            .limit(10)
        )

        result = self._session.execute(q)
        return [dict(r) for r in result.mappings().all()]

    def trips_count(self, line_number: str, start_date: date, end_date: date) -> int:
        """Count distinct trips for a line in the given period."""
        e = _stop_events.alias("e")
        # COUNT(DISTINCT (trip_id, service_date)) via subquery — equivalent, avoids row-constructor syntax.
        subq = (
            sa.select(e.c.trip_id, e.c.service_date)
            .distinct()
            .where(
                and_(
                    e.c.line_number == line_number,
                    e.c.service_date.between(start_date, end_date),
                )
            )
            .subquery()
        )
        result = self._session.execute(sa.select(func.count()).select_from(subq))
        return result.scalar() or 0

    def max_route_delay(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> list[dict[str, Any]]:
        """Route delay = delay at second-to-last stop - delay at second stop."""
        e = _stop_events.alias("e")

        filtered = (
            sa.select(
                e.c.trip_id,
                e.c.service_date,
                e.c.stop_sequence,
                e.c.stop_name,
                e.c.headsign,
                e.c.delay_seconds,
                e.c.line_number,
                e.c.license_plate,
                e.c.planned_time,
                e.c.event_time,
                e.c.max_stop_sequence,
                e.c.is_estimated,
            )
            .where(
                and_(
                    e.c.line_number == line_number,
                    e.c.service_date.between(start_date, end_date),
                    e.c.stop_sequence > 1,
                    e.c.stop_sequence < e.c.max_stop_sequence,
                    _det_filter(e, include_estimated),
                )
            )
            .cte("filtered")
        )

        trip_vehicle_check = (
            sa.select(
                filtered.c.trip_id,
                filtered.c.service_date,
                func.count(distinct(filtered.c.license_plate)).label("vehicle_count"),
            )
            .group_by(filtered.c.trip_id, filtered.c.service_date)
            .cte("trip_vehicle_check")
        )

        boundary_check = (
            sa.select(
                filtered.c.trip_id,
                filtered.c.service_date,
                filtered.c.max_stop_sequence,
                func.bool_or(filtered.c.stop_sequence == 2).label("has_second"),
                func.bool_or(filtered.c.stop_sequence == filtered.c.max_stop_sequence - 1).label("has_penultimate"),
            )
            .group_by(filtered.c.trip_id, filtered.c.service_date, filtered.c.max_stop_sequence)
            .cte("boundary_check")
        )

        bc = boundary_check
        tvc = trip_vehicle_check
        valid_trips = (
            sa.select(bc.c.trip_id, bc.c.service_date)
            .join(tvc, and_(bc.c.trip_id == tvc.c.trip_id, bc.c.service_date == tvc.c.service_date))
            .where(and_(bc.c.has_second, bc.c.has_penultimate, tvc.c.vehicle_count == 1))
            .cte("valid_trips")
        )

        part_by = [filtered.c.trip_id, filtered.c.service_date]
        order_by = filtered.c.stop_sequence

        vt = valid_trips
        trip_bounds = (
            sa.select(
                filtered.c.trip_id,
                filtered.c.service_date,
                filtered.c.headsign,
                filtered.c.line_number,
                filtered.c.license_plate,
                func.first_value(filtered.c.stop_name)
                .over(partition_by=part_by, order_by=order_by)
                .label("first_stop"),
                func.last_value(filtered.c.stop_name)
                .over(partition_by=part_by, order_by=order_by, rows=(None, None))
                .label("last_stop"),
                func.timezone(
                    _TZ, func.first_value(filtered.c.planned_time).over(partition_by=part_by, order_by=order_by)
                ).label("first_planned_time"),
                func.timezone(
                    _TZ, func.first_value(filtered.c.event_time).over(partition_by=part_by, order_by=order_by)
                ).label("first_event_time"),
                func.timezone(
                    _TZ,
                    func.last_value(filtered.c.planned_time).over(
                        partition_by=part_by, order_by=order_by, rows=(None, None)
                    ),
                ).label("last_planned_time"),
                func.timezone(
                    _TZ,
                    func.last_value(filtered.c.event_time).over(
                        partition_by=part_by, order_by=order_by, rows=(None, None)
                    ),
                ).label("last_event_time"),
                func.first_value(filtered.c.delay_seconds)
                .over(partition_by=part_by, order_by=order_by)
                .label("start_delay"),
                func.last_value(filtered.c.delay_seconds)
                .over(partition_by=part_by, order_by=order_by, rows=(None, None))
                .label("end_delay"),
                filtered.c.is_estimated,
            )
            .join(vt, and_(filtered.c.trip_id == vt.c.trip_id, filtered.c.service_date == vt.c.service_date))
            .cte("trip_bounds")
        )

        tb = trip_bounds
        delay_generated = (tb.c.end_delay - tb.c.start_delay).label("delay_generated_seconds")

        inner_q = (
            sa.select(
                tb.c.trip_id,
                tb.c.service_date,
                tb.c.line_number,
                tb.c.license_plate.label("vehicle_number"),
                tb.c.first_stop,
                tb.c.last_stop,
                tb.c.first_planned_time,
                tb.c.first_event_time,
                tb.c.last_planned_time,
                tb.c.last_event_time,
                tb.c.start_delay.label("start_delay_seconds"),
                tb.c.end_delay.label("end_delay_seconds"),
                delay_generated,
                tb.c.headsign,
                func.bool_or(tb.c.is_estimated)
                .over(partition_by=[tb.c.trip_id, tb.c.service_date])
                .label("is_estimated"),
            )
            .distinct(tb.c.trip_id, tb.c.service_date)
            .where(tb.c.start_delay >= MIN_DELAY_SECONDS)
            .order_by(tb.c.trip_id, tb.c.service_date, delay_generated.desc())
            .subquery("ranked")
        )

        q = sa.select(inner_q).order_by(inner_q.c.delay_generated_seconds.desc()).limit(10)

        result = self._session.execute(q)
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
        e = _stop_events.alias("e")

        q = sa.select(
            func.count().label("total"),
            func.count().filter(e.c.delay_seconds <= 120).label("on_time"),
            func.count().filter(and_(e.c.delay_seconds > 120, e.c.delay_seconds <= 360)).label("slightly_delayed"),
            func.count().filter(e.c.delay_seconds > 360).label("delayed"),
        ).where(
            and_(
                e.c.line_number == line_number,
                e.c.service_date.between(start_date, end_date),
                e.c.stop_sequence > 1,
                e.c.stop_sequence < e.c.max_stop_sequence,
                e.c.delay_seconds >= MIN_DELAY_SECONDS,
                _det_filter(e, include_estimated),
            )
        )

        row = self._session.execute(q).mappings().first()
        return dict(row) if row else {"total": 0, "on_time": 0, "slightly_delayed": 0, "delayed": 0}

    def trend(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> list[dict[str, Any]]:
        """Average delay per day for a line."""
        e = _stop_events.alias("e")

        q = (
            sa.select(
                e.c.service_date.label("date"),
                func.round(sa.cast(func.avg(e.c.delay_seconds), sa.Numeric), 1).label("avg_delay_seconds"),
                # Within each service_date group, COUNT(DISTINCT trip_id) == COUNT(DISTINCT (trip_id, service_date)).
                func.count(distinct(e.c.trip_id)).label("trips_count"),
            )
            .where(
                and_(
                    e.c.line_number == line_number,
                    e.c.service_date.between(start_date, end_date),
                    e.c.stop_sequence > 1,
                    e.c.stop_sequence < e.c.max_stop_sequence,
                    e.c.delay_seconds >= MIN_DELAY_SECONDS,
                    _det_filter(e, include_estimated),
                )
            )
            .group_by(e.c.service_date)
            .order_by(e.c.service_date)
        )

        result = self._session.execute(q)
        return [dict(r) for r in result.mappings().all()]
