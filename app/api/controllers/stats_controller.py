from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.api.constants import RATE_LIMIT_STATS
from app.api.db import DbSession
from app.api.middleware import limiter
from app.api.openapi import DOC_MAX_DELAY, DOC_PUNCTUALITY, DOC_ROUTE_DELAY, DOC_TREND
from app.api.repositories.stats_repository import StatsRepository
from app.api.response import MsgspecJSONResponse
from app.api.schemas import (
    EndDateQuery,
    IncludeEstimatedQuery,
    LineNumberPath,
    StartDateQuery,
)
from app.api.services.stats_service import StatsService
from app.api.validation import validate_date_range

router = APIRouter(prefix="/lines", tags=["statistics"])


def _get_service(db: DbSession) -> StatsService:
    return StatsService(StatsRepository(db))


Stats = Annotated[StatsService, Depends(_get_service)]


@router.get(
    "/{line_number}/stats/max-delay",
    openapi_extra=DOC_MAX_DELAY,
    summary="Top 10 delays between consecutive stops",
    response_model=None,
)
@limiter.limit(RATE_LIMIT_STATS)
def get_max_delay_between_stops(
    request: Request,
    line_number: LineNumberPath,
    service: Stats,
    start_date: StartDateQuery,
    end_date: EndDateQuery,
    include_estimated: IncludeEstimatedQuery = False,
) -> Response:
    """
    Returns a list of the Top 10 highest delay increments generated between two consecutive stops.

    ### Timezone
    All times are provided in Europe/Warsaw local time.

    ### Note
    The analysis covers stop sequences from 2 to n-1 (where n is the last stop of the trip).

    The first and last stops are intentionally excluded as they often contain garbage data
    (e.g., GPS drift during layovers, driver login delays).
    """
    validate_date_range(start_date, end_date)
    return MsgspecJSONResponse(
        service.max_delay_between_stops(line_number, start_date, end_date, include_estimated)
    )


@router.get(
    "/{line_number}/stats/route-delay",
    openapi_extra=DOC_ROUTE_DELAY,
    summary="Top 10 delays generated across entire route",
    response_model=None,
)
@limiter.limit(RATE_LIMIT_STATS)
def get_route_delay(
    request: Request,
    line_number: LineNumberPath,
    service: Stats,
    start_date: StartDateQuery,
    end_date: EndDateQuery,
    include_estimated: IncludeEstimatedQuery = False,
) -> Response:
    """
    Returns the Top 10 trips with the highest delay generated between the second stop
    and the penultimate stop of the route.

    ### Timezone
    All times are provided in Europe/Warsaw local time.

    ### Note
    The calculation is based on stop sequences from 2 to n-1 (where n is the last stop).

    The first and last stops are intentionally excluded as they often contain garbage data
    (e.g., GPS drift during layovers, driver login delays).
    """
    validate_date_range(start_date, end_date)
    return MsgspecJSONResponse(service.route_delay(line_number, start_date, end_date, include_estimated))


@router.get(
    "/{line_number}/stats/punctuality",
    openapi_extra=DOC_PUNCTUALITY,
    summary="Per-stop punctuality breakdown",
    response_model=None,
)
@limiter.limit(RATE_LIMIT_STATS)
def get_punctuality(
    request: Request,
    line_number: LineNumberPath,
    service: Stats,
    start_date: StartDateQuery,
    end_date: EndDateQuery,
    include_estimated: IncludeEstimatedQuery = False,
) -> Response:
    """
    Returns a punctuality breakdown for a specific line based on recorded stop events within the specified period.

    ### Punctuality Thresholds
    - **On-time**: delay <= 2 minutes (120s)
    - **Slightly delayed**: 2 minutes < delay <= 6 minutes (360s)
    - **Delayed**: delay > 6 minutes (360s)

    ### Timezone
    All times are provided in Europe/Warsaw local time.

    ### Note
    The calculation is based on stop sequences from 2 to n-1 (where n is the last stop).

    The first and last stops are intentionally excluded as they often contain garbage data
    (e.g., GPS drift during layovers, driver login delays).
    """
    validate_date_range(start_date, end_date)
    return MsgspecJSONResponse(service.punctuality(line_number, start_date, end_date, include_estimated))


@router.get(
    "/{line_number}/stats/trend",
    openapi_extra=DOC_TREND,
    summary="Daily average delay trend",
    response_model=None,
)
@limiter.limit(RATE_LIMIT_STATS)
def get_trend(
    request: Request,
    line_number: LineNumberPath,
    service: Stats,
    start_date: StartDateQuery,
    end_date: EndDateQuery,
    include_estimated: IncludeEstimatedQuery = False,
) -> Response:
    """
    Returns the daily average delay for a specific line over a period of time.

    ### Timezone
    All times are provided in Europe/Warsaw local time.

    ### Note
    The calculation is based on stop sequences from 2 to n-1 (where n is the last stop).

    The first and last stops are intentionally excluded as they often contain garbage data
    (e.g., GPS drift during layovers, driver login delays).
    """
    validate_date_range(start_date, end_date)
    return MsgspecJSONResponse(service.trend(line_number, start_date, end_date, include_estimated))
