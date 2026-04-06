from app.shared.models.enums import DetectionMethod, VehicleStatus
from app.shared.models.events import StopEvent
from app.stop_writer.detector.event_factory import EventFactory
from app.stop_writer.detector.strategies.base import DetectionContext
from app.stop_writer.repositories.saved_sequences import SavedSequencesRepository


class StoppedAtStrategy:
    def __init__(self, factory: EventFactory, saved_seqs: SavedSequencesRepository):
        self._factory = factory
        self._saved_seqs = saved_seqs

    def detect(self, ctx: DetectionContext) -> list[StopEvent]:
        if ctx.vp.status != VehicleStatus.STOPPED_AT:
            return []

        if self._saved_seqs.is_saved(ctx.agency_str, ctx.vp.trip_id, ctx.service_date, ctx.stop_sequence):
            return []

        event = self._factory.create(
            agency=ctx.vp.agency,
            trip_id=ctx.vp.trip_id,
            vehicle_id=ctx.vp.vehicle_id or None,
            license_plate=ctx.vp.license_plate,
            stop_sequence=ctx.stop_sequence,
            event_time=ctx.vp.timestamp,
            service_date=ctx.service_date,
            trip=ctx.trip,
            stop_time=ctx.stop_time,
            detection_method=DetectionMethod.STOPPED_AT,
            is_estimated=False,
        )
        return [event] if event else []
