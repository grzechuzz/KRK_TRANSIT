from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.common.constants import TIMEZONE
from app.common.db.models import CurrentStopTime, CurrentTrip
from app.common.gtfs.timeparse import compute_delay_seconds, compute_planned_time
from app.common.models.enums import DetectionMethod
from app.common.models.events import StopEvent
from app.common.models.gtfs_realtime import VehiclePosition
from app.stop_writer.detector.gtfs_cache import GtfsCache

TZ = ZoneInfo(TIMEZONE)


class EventFactory:
    def __init__(self, gtfs_cache: GtfsCache):
        self._cache = gtfs_cache

    def create(
        self,
        vp: VehiclePosition,
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

        static_hash = self._cache.get_current_hash(vp.agency)
        if not static_hash:
            return None

        max_seq = self._cache.get_max_stop_sequence(vp.trip_id)
        if not max_seq:
            return None

        planned_time = compute_planned_time(service_date, stop_time.arrival_seconds, TZ)
        delay_seconds = compute_delay_seconds(event_time, planned_time)

        return StopEvent(
            agency=vp.agency,
            trip_id=vp.trip_id,
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
            vehicle_id=vp.vehicle_id or None,
            license_plate=vp.license_plate,
            detection_method=detection_method,
            is_estimated=is_estimated,
            static_hash=static_hash,
            max_stop_sequence=max_seq,
        )
