from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.api import cache
from app.api.repositories.stats_repository import StatsRepository
from app.api.schemas import (
    MaxDelayBetweenStops,
    MaxDelayBetweenStopsResponse,
    PunctualityResponse,
    RouteDelay,
    RouteDelayResponse,
    TrendDay,
    TrendResponse,
)
from app.common.exceptions import ResourceNotFoundError


def _to_str(row: dict[str, Any]) -> dict[str, Any]:
    return {k: str(v) if not isinstance(v, (str, int, float)) else v for k, v in row.items()}


def _check_line_exists(trips: int, line_number: str, start_date: date, end_date: date) -> None:
    if not trips:
        raise ResourceNotFoundError("Line", line_number)


class StatsService:
    def __init__(self, db: Session):
        self._repo = StatsRepository(db)

    def max_delay_between_stops(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> bytes:
        cached = cache.get_cached("max-delay", line_number, start_date, end_date, include_estimated)
        if cached is not None:
            return cached

        trips = self._repo.trips_count(line_number, start_date, end_date)
        _check_line_exists(trips, line_number, start_date, end_date)

        rows = self._repo.max_delay_between_stops(line_number, start_date, end_date, include_estimated)

        result = MaxDelayBetweenStopsResponse(
            line_number=line_number,
            start_date=str(start_date),
            end_date=str(end_date),
            max_delay=[MaxDelayBetweenStops(**_to_str(row)) for row in rows],
            trips_analyzed=trips,
        )
        return cache.set_cached("max-delay", line_number, start_date, end_date, result, include_estimated)

    def route_delay(self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False) -> bytes:
        cached = cache.get_cached("route-delay", line_number, start_date, end_date, include_estimated)
        if cached is not None:
            return cached

        trips = self._repo.trips_count(line_number, start_date, end_date)
        _check_line_exists(trips, line_number, start_date, end_date)

        rows = self._repo.max_route_delay(line_number, start_date, end_date, include_estimated)

        result = RouteDelayResponse(
            line_number=line_number,
            start_date=str(start_date),
            end_date=str(end_date),
            max_route_delay=[RouteDelay(**_to_str(row)) for row in rows],
            trips_analyzed=trips,
        )
        return cache.set_cached("route-delay", line_number, start_date, end_date, result, include_estimated)

    def punctuality(self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False) -> bytes:
        cached = cache.get_cached("punctuality", line_number, start_date, end_date, include_estimated)
        if cached is not None:
            return cached

        trips = self._repo.trips_count(line_number, start_date, end_date)
        _check_line_exists(trips, line_number, start_date, end_date)

        row = self._repo.punctuality(line_number, start_date, end_date, include_estimated)
        total = row["total"]

        result = PunctualityResponse(
            line_number=line_number,
            start_date=str(start_date),
            end_date=str(end_date),
            total_stops=total,
            on_time_count=row["on_time"],
            on_time_percent=round(row["on_time"] / total * 100, 1) if total else 0.0,
            slightly_delayed_count=row["slightly_delayed"],
            slightly_delayed_percent=round(row["slightly_delayed"] / total * 100, 1) if total else 0.0,
            delayed_count=row["delayed"],
            delayed_percent=round(row["delayed"] / total * 100, 1) if total else 0.0,
        )
        return cache.set_cached("punctuality", line_number, start_date, end_date, result, include_estimated)

    def trend(self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False) -> bytes:
        cached = cache.get_cached("trend", line_number, start_date, end_date, include_estimated)
        if cached is not None:
            return cached

        trips = self._repo.trips_count(line_number, start_date, end_date)
        _check_line_exists(trips, line_number, start_date, end_date)

        rows = self._repo.trend(line_number, start_date, end_date, include_estimated)

        result = TrendResponse(
            line_number=line_number,
            start_date=str(start_date),
            end_date=str(end_date),
            days=[TrendDay(**_to_str(r)) for r in rows],
        )
        return cache.set_cached("trend", line_number, start_date, end_date, result, include_estimated)
