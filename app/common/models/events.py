from dataclasses import dataclass
from datetime import date, datetime

from app.common.models.enums import Agency, DetectionMethod


@dataclass(frozen=True)
class StopEvent:
    agency: Agency
    trip_id: str
    service_date: date
    stop_sequence: int
    stop_id: str
    line_number: str
    stop_name: str
    stop_desc: str | None
    direction_id: int | None
    headsign: str | None
    planned_time: datetime
    event_time: datetime
    delay_seconds: int
    vehicle_id: str | None
    license_plate: str | None
    detection_method: DetectionMethod
    is_estimated: bool
    static_hash: str
    max_stop_sequence: int
