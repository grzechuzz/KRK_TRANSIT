from app.common.models.enums import DetectionMethod
from app.common.models.events import StopEvent
from app.common.redis.repositories.saved_sequences import SavedSequencesRepository
from app.common.redis.repositories.trip_updates import TripUpdatesRepository
from app.stop_writer.detector.event_factory import EventFactory
from app.stop_writer.detector.gtfs_cache import GtfsCache
from app.stop_writer.detector.strategies.base import DetectionContext


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

        events: list[StopEvent] = []
        for missed_seq in range(prev_seq, curr_seq):
            if self._saved_seqs.is_saved(ctx.agency_str, ctx.vp.trip_id, ctx.service_date, missed_seq):
                continue

            event_time = self._trip_updates.get_arrival(ctx.agency_str, ctx.vp.trip_id, missed_seq)
            if not event_time:
                continue

            missed_stop_time = self._cache.get_stop_time(ctx.vp.trip_id, missed_seq)
            if not missed_stop_time:
                continue

            event = self._factory.create(
                vp=ctx.vp,
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
