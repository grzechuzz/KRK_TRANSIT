from datetime import UTC, datetime

import msgspec


class VehiclePositionMessage(msgspec.Struct):
    """Pub/Sub message published by rt_poller on vehicle_positions channel."""

    agency: str
    trip_id: str
    vehicle_id: str
    license_plate: str | None
    stop_id: str | None
    stop_sequence: int | None
    status: int | None
    timestamp: str  # ISO 8601


class LiveVehiclePosition(msgspec.Struct):
    """Live vehicle position cached by rt_poller in Redis."""

    agency: str
    license_plate: str
    trip_id: str
    latitude: float
    longitude: float
    bearing: float | None
    timestamp: datetime


class SavedSequenceData(msgspec.Struct):
    """Value stored per stop_sequence in the saved_sequences Redis hash."""

    delay: int
    event_time: datetime


class VehicleState(msgspec.Struct):
    """Current state of a tracked vehicle"""

    agency: str
    license_plate: str
    trip_id: str
    current_stop_sequence: int
    last_timestamp: datetime


class CachedStopTime(msgspec.Struct):
    """Cached arrival times for a single stop"""

    stop_id: str
    stop_sequence: int
    first_seen_arrival: datetime
    last_seen_arrival: datetime


class TripUpdateCache(msgspec.Struct):
    """Cached TripUpdate predictions for a trip"""

    agency: str
    trip_id: str
    stops: dict[int, CachedStopTime] = msgspec.field(default_factory=dict)  # stop_sequence -> CachedStopTime
    created_at: datetime = msgspec.field(default_factory=lambda: datetime.now(UTC))
    last_min_seq: int | None = None
