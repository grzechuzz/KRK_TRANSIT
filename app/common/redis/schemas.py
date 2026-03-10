from datetime import UTC, datetime

import msgspec


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
