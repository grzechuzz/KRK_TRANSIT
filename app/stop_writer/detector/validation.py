import logging
from datetime import date

from app.shared.models.enums import DetectionMethod
from app.shared.models.events import StopEvent
from app.stop_writer.constants import DELAY_DROP_THRESHOLD, MIN_EARLY_DELAY_SECONDS
from app.stop_writer.repositories.saved_sequences import SavedSequencesRepository

logger = logging.getLogger(__name__)


class EventValidator:
    def __init__(self, saved_seqs: SavedSequencesRepository):
        self._saved_seqs = saved_seqs

    @staticmethod
    def validate_in_batch(events: list[StopEvent]) -> list[StopEvent]:
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

    def validate_event(self, event: StopEvent, agency: str, trip_id: str, service_date: date) -> bool:
        if event.delay_seconds < MIN_EARLY_DELAY_SECONDS and event.stop_sequence != 1:
            logger.debug(
                "Rejected event trip=%s seq=%d: delay %ds below threshold",
                trip_id,
                event.stop_sequence,
                event.delay_seconds,
            )
            return False

        prev_seq = event.stop_sequence - 1
        if prev_seq < 1:
            return True

        prev_data = self._saved_seqs.get_saved_data(agency, trip_id, service_date, prev_seq)
        if prev_data is None:
            return True

        prev_delay, prev_event_time = prev_data

        if prev_delay - event.delay_seconds > DELAY_DROP_THRESHOLD:
            logger.debug(
                "Rejected event trip=%s seq=%d: delay drop %d -> %d",
                trip_id,
                event.stop_sequence,
                prev_delay,
                event.delay_seconds,
            )
            return False

        if prev_event_time >= event.event_time:
            logger.debug(
                "Rejected event trip=%s seq=%d: non-increasing time %s >= %s",
                trip_id,
                event.stop_sequence,
                prev_event_time,
                event.event_time,
            )
            return False

        return True
