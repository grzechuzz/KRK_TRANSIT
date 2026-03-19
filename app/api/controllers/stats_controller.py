from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api import schemas_docs as docs
from app.api.db import DbSession
from app.api.schemas import EndDateQuery, IncludeEstimatedQuery, LineNumberPath, StartDateQuery
from app.api.services.stats_service import StatsService
from app.api.validation import validate_date_range

router = APIRouter(prefix="/lines", tags=["statistics"])

JSON = "application/json"


def _get_service(db: DbSession) -> StatsService:
    return StatsService(db)


Stats = Annotated[StatsService, Depends(_get_service)]


@router.get(
    "/{line_number}/stats/max-delay",
    response_model=docs.MaxDelayBetweenStopsResponse,
    summary="Top 10 delays between consecutive stops",
)
def get_max_delay_between_stops(
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
    return Response(
        content=service.max_delay_between_stops(line_number, start_date, end_date, include_estimated),
        media_type=JSON,
    )


@router.get(
    "/{line_number}/stats/route-delay",
    response_model=docs.RouteDelayResponse,
    summary="Top 10 delays generated across entire route",
)
def get_route_delay(
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
    return Response(
        content=service.route_delay(line_number, start_date, end_date, include_estimated),
        media_type=JSON,
    )


@router.get(
    "/{line_number}/stats/punctuality",
    response_model=docs.PunctualityResponse,
    summary="Per-stop punctuality breakdown",
)
def get_punctuality(
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
    return Response(
        content=service.punctuality(line_number, start_date, end_date, include_estimated),
        media_type=JSON,
    )


@router.get(
    "/{line_number}/stats/trend",
    response_model=docs.TrendResponse,
    summary="Daily average delay trend",
)
def get_trend(
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
    return Response(
        content=service.trend(line_number, start_date, end_date, include_estimated),
        media_type=JSON,
    )
