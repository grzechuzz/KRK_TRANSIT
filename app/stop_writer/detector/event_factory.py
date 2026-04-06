from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.platform.constants import TIMEZONE
from app.shared.db.models import CurrentStopTime, CurrentTrip
from app.shared.gtfs.timeparse import compute_delay_seconds, compute_planned_time
from app.shared.models.enums import Agency, DetectionMethod
from app.shared.models.events import StopEvent
from app.stop_writer.detector.gtfs_cache import GtfsCache

TZ = ZoneInfo(TIMEZONE)


class EventFactory:
    def __init__(self, gtfs_cache: GtfsCache):
        self._cache = gtfs_cache

    def create(
        self,
        agency: Agency,
        trip_id: str,
        vehicle_id: str | None,
        license_plate: str | None,
        stop_sequence: int,
        event_time: datetime,
        service_date: date,
        trip: CurrentTrip,
        stop_time: CurrentStopTime,
        detection_method: DetectionMethod,
        is_estimated: bool,
    ) -> StopEvent | None:
        stop = self._cache.get_stop(stop_time.stop_id)
        if not stop:
            return None

        static_hash = self._cache.get_current_hash(agency)
        if not static_hash:
            return None

        max_seq = self._cache.get_max_stop_sequence(trip_id)
        if not max_seq:
            return None

        planned_time = compute_planned_time(service_date, stop_time.arrival_seconds, TZ)
        delay_seconds = compute_delay_seconds(event_time, planned_time)

        return StopEvent(
            agency=agency,
            trip_id=trip_id,
            service_date=service_date,
            stop_sequence=stop_sequence,
            stop_id=stop_time.stop_id,
            line_number=trip.route.route_short_name,
            stop_name=stop.stop_name,
            stop_desc=stop.stop_desc,
            direction_id=trip.direction_id,
            headsign=trip.headsign,
            planned_time=planned_time,
            event_time=event_time,
            delay_seconds=delay_seconds,
            vehicle_id=vehicle_id,
            license_plate=license_plate,
            detection_method=detection_method,
            is_estimated=is_estimated,
            static_hash=static_hash,
            max_stop_sequence=max_seq,
        )
