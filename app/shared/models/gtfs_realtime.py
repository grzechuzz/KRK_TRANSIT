from dataclasses import dataclass
from datetime import datetime

from app.shared.models.enums import Agency, VehicleStatus


@dataclass(frozen=True)
class VehiclePosition:
    """Parsed vehicle position from VehiclePositions.pb feed."""

    agency: Agency
    trip_id: str
    vehicle_id: str
    license_plate: str | None
    latitude: float | None
    longitude: float | None
    bearing: float | None
    stop_id: str | None
    stop_sequence: int | None
    status: VehicleStatus | None
    timestamp: datetime

    @property
    def has_position(self) -> bool:
        return self.latitude is not None and self.longitude is not None


@dataclass(frozen=True)
class StopTimeUpdate:
    """Single stop time update from TripUpdates.pb feed."""

    stop_id: str
    stop_sequence: int | None
    arrival_time: datetime | None
    departure_time: datetime | None


@dataclass(frozen=True)
class TripUpdate:
    """Parsed trip update from TripUpdates.pb feed."""

    agency: Agency
    trip_id: str
    vehicle_id: str | None
    timestamp: datetime
    stop_time_updates: list[StopTimeUpdate]
