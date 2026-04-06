from app.shared.models.enums import DetectionMethod
from app.shared.models.events import StopEvent
from app.shared.redis.repositories.trip_updates import TripUpdatesRepository
from app.stop_writer.detector.event_factory import EventFactory
from app.stop_writer.detector.gtfs_cache import GtfsCache
from app.stop_writer.detector.strategies.base import DetectionContext
from app.stop_writer.repositories.saved_sequences import SavedSequencesRepository


class SeqJumpStrategy:
    def __init__(
        self,
        factory: EventFactory,
        gtfs_cache: GtfsCache,
        saved_seqs: SavedSequencesRepository,
        trip_updates: TripUpdatesRepository,
    ):
        self._factory = factory
        self._cache = gtfs_cache
        self._saved_seqs = saved_seqs
        self._trip_updates = trip_updates

    def detect(self, ctx: DetectionContext) -> list[StopEvent]:
        if not ctx.prev_state or ctx.prev_state.trip_id != ctx.vp.trip_id:
            return []

        prev_seq = ctx.prev_state.current_stop_sequence
        curr_seq = ctx.stop_sequence

        if curr_seq <= prev_seq:
            return []

        already_saved = self._saved_seqs.get_all_sequences(ctx.agency_str, ctx.vp.trip_id, ctx.service_date)
        trip_cache = self._trip_updates.get(ctx.agency_str, ctx.vp.trip_id)

        events: list[StopEvent] = []
        for missed_seq in range(prev_seq, curr_seq):
            if missed_seq in already_saved:
                continue

            if trip_cache is None:
                continue
            cached_stop = trip_cache.stops.get(missed_seq)
            if cached_stop is None:
                continue
            event_time = cached_stop.last_seen_arrival

            missed_stop_time = self._cache.get_stop_time(ctx.vp.trip_id, missed_seq)
            if not missed_stop_time:
                continue

            event = self._factory.create(
                agency=ctx.vp.agency,
                trip_id=ctx.vp.trip_id,
                vehicle_id=ctx.vp.vehicle_id or None,
                license_plate=ctx.vp.license_plate,
                stop_sequence=missed_seq,
                event_time=event_time,
                service_date=ctx.service_date,
                trip=ctx.trip,
                stop_time=missed_stop_time,
                detection_method=DetectionMethod.SEQ_JUMP,
                is_estimated=True,
            )
            if event:
                events.append(event)

        return events
