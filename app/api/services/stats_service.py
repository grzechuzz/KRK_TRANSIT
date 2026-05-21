import logging
from datetime import date
from typing import Any, cast

import msgspec

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
from app.shared.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


def _to_str(row: dict[str, Any]) -> dict[str, Any]:
    return {k: str(v) if not isinstance(v, (str, int, float)) else v for k, v in row.items()}


def _to_jsonable(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, bool):
            normalized[key] = value
        elif isinstance(value, int | float | str):
            normalized[key] = value
        else:
            try:
                normalized[key] = float(value)
            except (TypeError, ValueError):
                normalized[key] = str(value)
    return normalized


def _decode_cached_or_none(cached: bytes | None, response_type: Any, endpoint: str) -> Any | None:
    if cached is None:
        return None
    try:
        return msgspec.json.decode(cached, type=response_type)
    except msgspec.ValidationError:
        logger.warning("Invalid stats cache payload for endpoint=%s; rebuilding", endpoint, exc_info=True)
        return None


def _check_line_exists(trips: int, line_number: str, start_date: date, end_date: date) -> None:
    if not trips:
        raise ResourceNotFoundError("Line", line_number)


class StatsService:
    def __init__(self, repo: StatsRepository):
        self._repo = repo

    def max_delay_between_stops(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> MaxDelayBetweenStopsResponse:
        cached = cache.get_cached("max-delay", line_number, start_date, end_date, include_estimated)
        decoded = _decode_cached_or_none(cached, MaxDelayBetweenStopsResponse, "max-delay")
        if decoded is not None:
            return cast(MaxDelayBetweenStopsResponse, decoded)

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
        cache.set_cached("max-delay", line_number, start_date, end_date, result, include_estimated)
        return result

    def route_delay(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> RouteDelayResponse:
        cached = cache.get_cached("route-delay", line_number, start_date, end_date, include_estimated)
        decoded = _decode_cached_or_none(cached, RouteDelayResponse, "route-delay")
        if decoded is not None:
            return cast(RouteDelayResponse, decoded)

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
        cache.set_cached("route-delay", line_number, start_date, end_date, result, include_estimated)
        return result

    def punctuality(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> PunctualityResponse:
        cached = cache.get_cached("punctuality", line_number, start_date, end_date, include_estimated)
        decoded = _decode_cached_or_none(cached, PunctualityResponse, "punctuality")
        if decoded is not None:
            return cast(PunctualityResponse, decoded)

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
        cache.set_cached("punctuality", line_number, start_date, end_date, result, include_estimated)
        return result

    def trend(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> TrendResponse:
        cached = cache.get_cached("trend", line_number, start_date, end_date, include_estimated)
        decoded = _decode_cached_or_none(cached, TrendResponse, "trend")
        if decoded is not None:
            return cast(TrendResponse, decoded)

        trips = self._repo.trips_count(line_number, start_date, end_date)
        _check_line_exists(trips, line_number, start_date, end_date)

        rows = self._repo.trend(line_number, start_date, end_date, include_estimated)

        result = TrendResponse(
            line_number=line_number,
            start_date=str(start_date),
            end_date=str(end_date),
            days=[TrendDay(**_to_jsonable(r)) for r in rows],
        )
        cache.set_cached("trend", line_number, start_date, end_date, result, include_estimated)
        return result
