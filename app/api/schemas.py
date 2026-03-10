from datetime import date
from typing import Annotated

import msgspec
from fastapi import Path, Query

StartDateQuery = Annotated[
    date,
    Query(
        description="Start service date (inclusive), e.g. 2026-02-01. "
        "Note: overnight trips (lines 6XX, 9XX) belong to the previous service date."
    ),
]
EndDateQuery = Annotated[
    date,
    Query(
        description="End service date (inclusive), e.g. 2026-02-13. "
        "Note: overnight trips (lines 6XX, 9XX) belong to the previous service date."
    ),
]

LineNumberPath = Annotated[
    str,
    Path(
        description="Line number, e.g. 194, 424, 503",
        min_length=1,
        max_length=5,
        pattern=r"^[a-zA-Z0-9]{1,5}$",
    ),
]

ShapeIdPath = Annotated[
    str,
    Path(
        description="Shape ID from /vehicles/positions endpoint",
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]{1,50}$",
    ),
]


class MaxDelayBetweenStops(msgspec.Struct):
    trip_id: str
    line_number: str
    vehicle_number: str
    from_stop: str
    to_stop: str
    from_sequence: int
    to_sequence: int
    from_planned_time: str
    from_event_time: str
    to_planned_time: str
    to_event_time: str
    delay_generated_seconds: int
    headsign: str
    service_date: str


class MaxDelayBetweenStopsResponse(msgspec.Struct):
    line_number: str
    start_date: str
    end_date: str
    max_delay: list[MaxDelayBetweenStops]
    trips_analyzed: int


class RouteDelay(msgspec.Struct):
    trip_id: str
    line_number: str
    vehicle_number: str
    first_stop: str
    last_stop: str
    first_planned_time: str
    first_event_time: str
    last_planned_time: str
    last_event_time: str
    start_delay_seconds: int
    end_delay_seconds: int
    delay_generated_seconds: int
    headsign: str
    service_date: str


class RouteDelayResponse(msgspec.Struct):
    line_number: str
    start_date: str
    end_date: str
    max_route_delay: list[RouteDelay]
    trips_analyzed: int


class PunctualityResponse(msgspec.Struct):
    """
    Thresholds:
    - on_time: delay <= 120s (2 min)
    - slightly_delayed: 120s < delay <= 360s (2-6 min)
    - delayed: delay > 360s (6+ min)
    """

    line_number: str
    start_date: str
    end_date: str
    total_stops: int
    on_time_count: int
    on_time_percent: float
    slightly_delayed_count: int
    slightly_delayed_percent: float
    delayed_count: int
    delayed_percent: float


class TrendDay(msgspec.Struct):
    date: str
    avg_delay_seconds: float
    trips_count: int


class TrendResponse(msgspec.Struct):
    line_number: str
    start_date: str
    end_date: str
    days: list[TrendDay]


class LiveVehicle(msgspec.Struct):
    trip_id: str
    license_plate: str
    line_number: str
    headsign: str
    shape_id: str | None
    latitude: float
    longitude: float
    bearing: float | None
    timestamp: str


class LiveVehicleResponse(msgspec.Struct):
    count: int
    vehicles: list[LiveVehicle]


class ShapePoint(msgspec.Struct):
    latitude: float
    longitude: float
    sequence: int


class ShapeResponse(msgspec.Struct):
    shape_id: str
    points: list[ShapePoint]
