from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.common.db.models import CurrentStopTime, CurrentTrip
from app.common.models.events import StopEvent
from app.common.models.gtfs_realtime import VehiclePosition
from app.common.redis.schemas import VehicleState


@dataclass(frozen=True)
class DetectionContext:
    vp: VehiclePosition
    prev_state: VehicleState | None
    agency_str: str
    service_date: date
    trip: CurrentTrip
    stop_time: CurrentStopTime
    stop_sequence: int


class DetectionStrategy(Protocol):
    def detect(self, ctx: DetectionContext) -> list[StopEvent]: ...
