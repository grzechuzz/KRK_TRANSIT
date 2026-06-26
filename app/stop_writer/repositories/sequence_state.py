from datetime import date, datetime
from typing import Protocol

from app.shared.models.events import StopEvent
from app.stop_writer.repositories.saved_sequences import SavedSequencesRepository

SequenceKey = tuple[str, str, date]
SequenceValue = tuple[int, datetime]


class SequenceStateReader(Protocol):
    def is_saved(self, agency: str, trip_id: str, service_date: date, stop_sequence: int) -> bool: ...

    def get_all_sequences(self, agency: str, trip_id: str, service_date: date) -> set[int]: ...

    def get_saved_data(
        self, agency: str, trip_id: str, service_date: date, stop_sequence: int
    ) -> tuple[int, datetime] | None: ...


class PendingSequenceState:
    def __init__(self, saved_sequences: SavedSequencesRepository) -> None:
        self._saved_sequences = saved_sequences
        self._pending: dict[SequenceKey, dict[int, SequenceValue]] = {}

    def is_saved(self, agency: str, trip_id: str, service_date: date, stop_sequence: int) -> bool:
        if stop_sequence in self._pending.get((agency, trip_id, service_date), {}):
            return True
        return self._saved_sequences.is_saved(agency, trip_id, service_date, stop_sequence)

    def get_all_sequences(self, agency: str, trip_id: str, service_date: date) -> set[int]:
        saved = self._saved_sequences.get_all_sequences(agency, trip_id, service_date)
        pending = set(self._pending.get((agency, trip_id, service_date), {}))
        return saved | pending

    def get_saved_data(
        self, agency: str, trip_id: str, service_date: date, stop_sequence: int
    ) -> tuple[int, datetime] | None:
        pending = self._pending.get((agency, trip_id, service_date), {})
        if stop_sequence in pending:
            return pending[stop_sequence]
        return self._saved_sequences.get_saved_data(agency, trip_id, service_date, stop_sequence)

    def add_pending(self, events: list[StopEvent]) -> None:
        for event in events:
            key = self._event_key(event)
            self._pending.setdefault(key, {})[event.stop_sequence] = (event.delay_seconds, event.event_time)

    def mark_committed(self, events: list[StopEvent]) -> None:
        for event in events:
            agency = event.agency.value
            self._saved_sequences.mark_saved(
                agency,
                event.trip_id,
                event.service_date,
                event.stop_sequence,
                event.delay_seconds,
                event.event_time,
            )
            self._remove_pending(event)

    def with_candidates(self) -> "CandidateSequenceState":
        return CandidateSequenceState(self)

    @staticmethod
    def _event_key(event: StopEvent) -> SequenceKey:
        return event.agency.value, event.trip_id, event.service_date

    def _remove_pending(self, event: StopEvent) -> None:
        key = self._event_key(event)
        pending_for_trip = self._pending.get(key)
        if pending_for_trip is None:
            return

        pending_for_trip.pop(event.stop_sequence, None)
        if not pending_for_trip:
            self._pending.pop(key, None)


class CandidateSequenceState:
    def __init__(self, base: SequenceStateReader) -> None:
        self._base = base
        self._candidates: dict[SequenceKey, dict[int, SequenceValue]] = {}

    def is_saved(self, agency: str, trip_id: str, service_date: date, stop_sequence: int) -> bool:
        if stop_sequence in self._candidates.get((agency, trip_id, service_date), {}):
            return True
        return self._base.is_saved(agency, trip_id, service_date, stop_sequence)

    def get_all_sequences(self, agency: str, trip_id: str, service_date: date) -> set[int]:
        saved = self._base.get_all_sequences(agency, trip_id, service_date)
        candidates = set(self._candidates.get((agency, trip_id, service_date), {}))
        return saved | candidates

    def get_saved_data(
        self, agency: str, trip_id: str, service_date: date, stop_sequence: int
    ) -> tuple[int, datetime] | None:
        candidates = self._candidates.get((agency, trip_id, service_date), {})
        if stop_sequence in candidates:
            return candidates[stop_sequence]
        return self._base.get_saved_data(agency, trip_id, service_date, stop_sequence)

    def add_candidate(self, event: StopEvent) -> None:
        key = event.agency.value, event.trip_id, event.service_date
        self._candidates.setdefault(key, {})[event.stop_sequence] = (event.delay_seconds, event.event_time)
