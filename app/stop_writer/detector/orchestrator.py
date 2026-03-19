from datetime import date

from sqlalchemy.orm import Session

from app.common.gtfs.timeparse import compute_service_date
from app.common.models.events import StopEvent
from app.common.models.gtfs_realtime import VehiclePosition
from app.common.redis.repositories.saved_sequences import SavedSequencesRepository
from app.common.redis.repositories.trip_updates import TripUpdatesRepository
from app.common.redis.repositories.vehicle_state import VehicleStateRepository
from app.common.redis.schemas import VehicleState
from app.stop_writer.detector.event_factory import EventFactory
from app.stop_writer.detector.gtfs_cache import GtfsCache
from app.stop_writer.detector.strategies.base import DetectionContext, DetectionStrategy
from app.stop_writer.detector.strategies.seq_jump import SeqJumpStrategy
from app.stop_writer.detector.strategies.stopped_at import StoppedAtStrategy
from app.stop_writer.detector.strategies.trip_completion import TripFinalizer
from app.stop_writer.detector.validation import EventValidator


class StopEventDetector:
    def __init__(
        self,
        session: Session,
        redis_vehicle_state: VehicleStateRepository,
        redis_trip_updates: TripUpdatesRepository,
        redis_saved_seqs: SavedSequencesRepository,
    ):
        self._vehicle_state = redis_vehicle_state
        self._trip_updates = redis_trip_updates
        self._saved_seqs = redis_saved_seqs

        gtfs_cache = GtfsCache(session)
        factory = EventFactory(gtfs_cache)

        self._strategies: list[DetectionStrategy] = [
            StoppedAtStrategy(factory, redis_saved_seqs),
            SeqJumpStrategy(factory, gtfs_cache, redis_saved_seqs, redis_trip_updates),
        ]
        self._finalizer = TripFinalizer(factory, gtfs_cache, redis_saved_seqs, redis_trip_updates)
        self._validator = EventValidator(redis_saved_seqs)
        self._gtfs_cache = gtfs_cache

    def process_update(self, vp: VehiclePosition) -> list[StopEvent]:
        if vp.stop_sequence is None or vp.license_plate is None:
            return []

        agency_str = vp.agency.value
        prev_state = self._vehicle_state.get(agency_str, vp.license_plate)

        # Trip changed - finalize old trip, then clean up Redis state
        completion_events: list[StopEvent] = []
        if prev_state and prev_state.trip_id != vp.trip_id:
            raw_events = self._finalizer.finalize(prev_state)
            completion_events = self._persist_events(raw_events, prev_state.agency, prev_state.trip_id)
            self._trip_updates.delete(agency_str, prev_state.trip_id)
            self._vehicle_state.delete(agency_str, prev_state.license_plate)
            prev_state = None

        trip = self._gtfs_cache.get_trip(vp.trip_id)
        if not trip:
            return completion_events

        stop_time = self._gtfs_cache.get_stop_time(vp.trip_id, vp.stop_sequence)
        if not stop_time:
            return completion_events

        service_date = compute_service_date(vp.timestamp, stop_time.arrival_seconds)

        ctx = DetectionContext(
            vp=vp,
            prev_state=prev_state,
            agency_str=agency_str,
            service_date=service_date,
            trip=trip,
            stop_time=stop_time,
            stop_sequence=vp.stop_sequence,
        )

        # Run all strategies, collect raw events
        detected: list[StopEvent] = []
        for strategy in self._strategies:
            detected.extend(strategy.detect(ctx))

        # Validate + persist (single place for all side-effects)
        detection_events = self._persist_events(detected, agency_str, vp.trip_id, service_date)

        # In-batch validation when STOPPED_AT + estimated events in same update
        if vp.status and vp.status.value == 1 and len(detection_events) > 1:
            detection_events = self._validator.validate_in_batch(detection_events)

        # Save vehicle state
        new_state = VehicleState(
            agency=agency_str,
            license_plate=vp.license_plate,
            trip_id=vp.trip_id,
            current_stop_sequence=ctx.stop_sequence,
            last_timestamp=vp.timestamp,
        )
        self._vehicle_state.save(new_state)

        return completion_events + detection_events

    def _persist_events(
        self,
        raw_events: list[StopEvent],
        agency_str: str,
        trip_id: str,
        service_date: date | None = None,
    ) -> list[StopEvent]:
        validated: list[StopEvent] = []
        for event in raw_events:
            sd = service_date or event.service_date
            if not self._validator.validate_event(event, agency_str, trip_id, sd):
                continue
            validated.append(event)
            self._saved_seqs.mark_saved(
                agency_str,
                trip_id,
                sd,
                event.stop_sequence,
                event.delay_seconds,
                event.event_time,
            )
        return validated
