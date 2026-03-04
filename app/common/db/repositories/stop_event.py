from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.common.db.models import StopEventModel
from app.common.models.events import StopEvent


class StopEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert_batch(self, events: list[StopEvent]) -> int:
        rows = []
        for event in events:
            rows.append(
                {
                    "agency": event.agency.value,
                    "trip_id": event.trip_id,
                    "service_date": event.service_date,
                    "stop_sequence": event.stop_sequence,
                    "stop_id": event.stop_id,
                    "line_number": event.line_number,
                    "stop_name": event.stop_name,
                    "stop_desc": event.stop_desc,
                    "direction_id": event.direction_id,
                    "headsign": event.headsign,
                    "planned_time": event.planned_time,
                    "event_time": event.event_time,
                    "delay_seconds": event.delay_seconds,
                    "vehicle_id": event.vehicle_id,
                    "license_plate": event.license_plate,
                    "detection_method": event.detection_method.value,
                    "is_estimated": event.is_estimated,
                    "static_hash": event.static_hash,
                    "max_stop_sequence": event.max_stop_sequence,
                }
            )

        if not rows:
            return 0

        stmt = insert(StopEventModel).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["trip_id", "service_date", "stop_sequence"])

        self._session.execute(stmt)
        return len(rows)
