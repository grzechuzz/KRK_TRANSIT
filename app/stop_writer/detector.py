from datetime import date, datetime
from zoneinfo import ZoneInfo

from cachetools import LRUCache
from sqlalchemy.orm import Session

from app.common.constants import (
    CACHE_MAX_SEQUENCES,
    CACHE_MAX_STOP_TIMES,
    CACHE_MAX_STOPS,
    CACHE_MAX_TRIPS,
    DELAY_DROP_THRESHOLD,
)
from app.common.db.models import CurrentStop, CurrentStopTime, CurrentTrip
from app.common.db.repositories.gtfs_meta import GtfsMetaRepository
from app.common.db.repositories.gtfs_static import GtfsStaticRepository
from app.common.gtfs.timeparse import compute_delay_seconds, compute_planned_time, compute_service_date
from app.common.models.enums import Agency, DetectionMethod
from app.common.models.events import StopEvent
from app.common.models.gtfs_realtime import VehiclePosition
from app.common.redis.repositories.saved_sequences import SavedSequencesRepository
from app.common.redis.repositories.trip_updates import TripUpdatesRepository
from app.common.redis.repositories.vehicle_state import VehicleStateRepository
from app.common.redis.schemas import VehicleState

TZ = ZoneInfo("Europe/Warsaw")


class StopEventDetector:
    def __init__(
        self,
        session: Session,
        redis_vehicle_state: VehicleStateRepository,
        redis_trip_updates: TripUpdatesRepository,
        redis_saved_seqs: SavedSequencesRepository,
    ):
        self._session = session
        self._static_repo = GtfsStaticRepository(session)
        self._meta_repo = GtfsMetaRepository(session)
        self._vehicle_state = redis_vehicle_state
        self._trip_updates = redis_trip_updates
        self._saved_seqs = redis_saved_seqs

        self._trip_cache: LRUCache[str, CurrentTrip] = LRUCache(maxsize=CACHE_MAX_TRIPS)
        self._stop_cache: LRUCache[str, CurrentStop] = LRUCache(maxsize=CACHE_MAX_STOPS)
        self._stop_times_cache: LRUCache[str, dict[int, CurrentStopTime]] = LRUCache(maxsize=CACHE_MAX_STOP_TIMES)
        self._max_seq_cache: LRUCache[str, int] = LRUCache(maxsize=CACHE_MAX_SEQUENCES)

    def process_update(self, vp: VehiclePosition) -> list[StopEvent]:
        if vp.stop_sequence is None or vp.license_plate is None:
            return []

        events: list[StopEvent] = []
        agency_str = vp.agency.value

        prev_state = self._vehicle_state.get(agency_str, vp.license_plate)

        if prev_state and prev_state.trip_id != vp.trip_id:
            completion_events = self._complete_trip(prev_state)
            events.extend(completion_events)
            prev_state = None

        trip = self._get_trip(vp.trip_id)
        if not trip:
            return events

        stop_time = self._get_stop_time(vp.trip_id, vp.stop_sequence)
        if not stop_time:
            return events

        service_date = compute_service_date(vp.timestamp, stop_time.arrival_seconds)

        if vp.status and vp.status.value == 1:
            if not self._saved_seqs.is_saved(agency_str, vp.trip_id, service_date, vp.stop_sequence):
                event = self._create_event(
                    vp=vp,
                    stop_sequence=vp.stop_sequence,
                    event_time=vp.timestamp,
                    service_date=service_date,
                    trip=trip,
                    stop_time=stop_time,
                    detection_method=DetectionMethod.STOPPED_AT,
                    is_estimated=False,
                )
                if event:
                    events.append(event)
                    self._saved_seqs.mark_saved(agency_str, vp.trip_id, service_date, vp.stop_sequence)

        if prev_state and prev_state.trip_id == vp.trip_id:
            prev_seq = prev_state.current_stop_sequence
            curr_seq = vp.stop_sequence

            if curr_seq > prev_seq:
                for missed_seq in range(prev_seq, curr_seq):
                    if self._saved_seqs.is_saved(agency_str, vp.trip_id, service_date, missed_seq):
                        continue

                    event_time: datetime | None = None
                    detection_method = DetectionMethod.SEQ_JUMP

                    if prev_state.incoming_at_sequence == missed_seq and prev_state.incoming_at_timestamp is not None:
                        event_time = prev_state.incoming_at_timestamp
                        detection_method = DetectionMethod.INCOMING_AT

                    if event_time is None:
                        event_time = self._trip_updates.get_arrival(agency_str, vp.trip_id, missed_seq)

                    if not event_time:
                        continue

                    missed_stop_time = self._get_stop_time(vp.trip_id, missed_seq)
                    if not missed_stop_time:
                        continue

                    event = self._create_event(
                        vp=vp,
                        stop_sequence=missed_seq,
                        event_time=event_time,
                        service_date=service_date,
                        trip=trip,
                        stop_time=missed_stop_time,
                        detection_method=detection_method,
                        is_estimated=(detection_method == DetectionMethod.SEQ_JUMP),
                    )
                    if event:
                        events.append(event)
                        self._saved_seqs.mark_saved(agency_str, vp.trip_id, service_date, missed_seq)

        if vp.status and vp.status.value == 1 and len(events) > 1:
            events = self._validate_estimated_events(events)

        incoming_seq = prev_state.incoming_at_sequence if prev_state else None
        incoming_ts = prev_state.incoming_at_timestamp if prev_state else None

        if vp.status and vp.status.value == 0:
            incoming_seq = vp.stop_sequence
            incoming_ts = vp.timestamp
        elif vp.status and vp.status.value == 1:
            incoming_seq = None
            incoming_ts = None

        new_state = VehicleState(
            agency=agency_str,
            license_plate=vp.license_plate,
            trip_id=vp.trip_id,
            current_stop_sequence=vp.stop_sequence,
            last_timestamp=vp.timestamp,
            incoming_at_sequence=incoming_seq,
            incoming_at_timestamp=incoming_ts,
        )
        self._vehicle_state.save(new_state)

        return events

    @staticmethod
    def _validate_estimated_events(events: list[StopEvent]) -> list[StopEvent]:
        stopped_at_events = [e for e in events if e.detection_method == DetectionMethod.STOPPED_AT]
        if not stopped_at_events:
            return events

        reference = stopped_at_events[-1]

        validated: list[StopEvent] = []
        for event in events:
            if not event.is_estimated:
                validated.append(event)
                continue

            if event.stop_sequence >= reference.stop_sequence:
                validated.append(event)
                continue

            if event.event_time > reference.event_time:
                continue

            if event.delay_seconds - reference.delay_seconds > DELAY_DROP_THRESHOLD:
                continue

            validated.append(event)

        return validated

    def _complete_trip(self, prev_state: VehicleState) -> list[StopEvent]:
        events: list[StopEvent] = []
        agency_str = prev_state.agency
        trip_id = prev_state.trip_id

        trip = self._get_trip(trip_id)
        if not trip:
            return events

        max_seq = self._get_max_stop_sequence(trip_id)
        if not max_seq:
            return events

        for seq in range(prev_state.current_stop_sequence + 1, max_seq + 1):
            stop_time = self._get_stop_time(trip_id, seq)
            if not stop_time:
                continue

            service_date = compute_service_date(prev_state.last_timestamp, stop_time.arrival_seconds)

            if self._saved_seqs.is_saved(agency_str, trip_id, service_date, seq):
                continue

            event_time: datetime | None = None
            detection_method = DetectionMethod.SEQ_JUMP

            if prev_state.incoming_at_sequence == seq and prev_state.incoming_at_timestamp is not None:
                event_time = prev_state.incoming_at_timestamp
                detection_method = DetectionMethod.INCOMING_AT

            if event_time is None:
                cache = self._trip_updates.get(agency_str, trip_id)
                if not cache:
                    continue

                cached_stop = cache.stops.get(seq)
                if not cached_stop:
                    continue

                if seq == max_seq:
                    event_time = cached_stop.first_seen_arrival
                    detection_method = DetectionMethod.TIMEOUT
                else:
                    event_time = cached_stop.last_seen_arrival

            is_estimated = detection_method in (DetectionMethod.SEQ_JUMP, DetectionMethod.TIMEOUT)

            dummy_vp = VehiclePosition(
                agency=Agency(agency_str),
                trip_id=trip_id,
                vehicle_id="",
                license_plate=prev_state.license_plate,
                latitude=None,
                longitude=None,
                bearing=None,
                stop_id=stop_time.stop_id,
                stop_sequence=seq,
                status=None,
                timestamp=event_time,
            )

            event = self._create_event(
                vp=dummy_vp,
                stop_sequence=seq,
                event_time=event_time,
                service_date=service_date,
                trip=trip,
                stop_time=stop_time,
                detection_method=detection_method,
                is_estimated=is_estimated,
            )
            if event:
                events.append(event)
                self._saved_seqs.mark_saved(agency_str, trip_id, service_date, seq)

        self._trip_updates.delete(agency_str, trip_id)
        self._vehicle_state.delete(agency_str, prev_state.license_plate)

        return events

    def _create_event(
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
        stop = self._get_stop(stop_time.stop_id)
        if not stop:
            return None

        static_hash = self._meta_repo.get_current_hash(vp.agency)
        if not static_hash:
            return None

        max_seq = self._get_max_stop_sequence(vp.trip_id)
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

    def _get_trip(self, trip_id: str) -> CurrentTrip | None:
        if trip_id not in self._trip_cache:
            trip = self._static_repo.get_trip(trip_id)
            if trip:
                self._trip_cache[trip_id] = trip
        return self._trip_cache.get(trip_id)

    def _get_stop(self, stop_id: str) -> CurrentStop | None:
        if stop_id not in self._stop_cache:
            stop = self._static_repo.get_stop(stop_id)
            if stop:
                self._stop_cache[stop_id] = stop
        return self._stop_cache.get(stop_id)

    def _get_stop_time(self, trip_id: str, stop_sequence: int) -> CurrentStopTime | None:
        if trip_id not in self._stop_times_cache:
            stop_times = self._static_repo.get_stop_times_for_trip(trip_id)
            self._stop_times_cache[trip_id] = {st.stop_sequence: st for st in stop_times}
        return self._stop_times_cache.get(trip_id, {}).get(stop_sequence)

    def _get_max_stop_sequence(self, trip_id: str) -> int | None:
        if trip_id not in self._max_seq_cache:
            max_seq = self._static_repo.get_max_stop_sequence(trip_id)
            if max_seq:
                self._max_seq_cache[trip_id] = max_seq
        return self._max_seq_cache.get(trip_id)
