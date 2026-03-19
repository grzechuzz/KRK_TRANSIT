from datetime import UTC, date, datetime
from unittest.mock import MagicMock

from app.common.models.enums import Agency, DetectionMethod
from app.common.models.events import StopEvent
from app.stop_writer.detector.validation import EventValidator


def _make_event(
    stop_sequence: int = 5,
    delay_seconds: int = 30,
    event_time: datetime | None = None,
) -> StopEvent:
    return StopEvent(
        agency=Agency.MPK,
        trip_id="trip_1",
        service_date=date(2026, 2, 9),
        stop_sequence=stop_sequence,
        stop_id=f"stop_{stop_sequence}",
        line_number="152",
        stop_name="Rondo Mogilskie",
        stop_desc="01",
        direction_id=0,
        headsign="Dworzec Główny",
        planned_time=datetime(2026, 2, 9, 12, 0, 0, tzinfo=UTC),
        event_time=event_time or datetime(2026, 2, 9, 12, 0, 30, tzinfo=UTC),
        delay_seconds=delay_seconds,
        vehicle_id="v1",
        license_plate="AB123",
        detection_method=DetectionMethod.SEQ_JUMP,
        is_estimated=True,
        static_hash="abc123hash",
        max_stop_sequence=10,
    )


SERVICE_DATE = date(2026, 2, 9)


# MIN_EARLY_DELAY rule

def test_min_delay_rejects_below_threshold():
    mock_saved = MagicMock()
    mock_saved.get_saved_data.return_value = None
    validator = EventValidator(mock_saved)

    event = _make_event(stop_sequence=5, delay_seconds=-200)

    assert validator.validate_event(event, "mpk", "trip_1", SERVICE_DATE) is False


def test_min_delay_allows_seq_1():
    mock_saved = MagicMock()
    mock_saved.get_saved_data.return_value = None
    validator = EventValidator(mock_saved)

    event = _make_event(stop_sequence=1, delay_seconds=-200)

    assert validator.validate_event(event, "mpk", "trip_1", SERVICE_DATE) is True


# DELAY_DROP rule

def test_delay_drop_rejects_large_drop():
    mock_saved = MagicMock()
    # Previous stop had delay=300, current has delay=0 → drop of 300 > 180
    mock_saved.get_saved_data.return_value = (300, datetime(2026, 2, 9, 11, 59, 0, tzinfo=UTC))
    validator = EventValidator(mock_saved)

    event = _make_event(stop_sequence=5, delay_seconds=0, event_time=datetime(2026, 2, 9, 12, 0, 0, tzinfo=UTC))

    assert validator.validate_event(event, "mpk", "trip_1", SERVICE_DATE) is False


def test_delay_drop_allows_small_drop():
    mock_saved = MagicMock()
    # Previous delay=100, current=0 → drop of 100 < 180
    mock_saved.get_saved_data.return_value = (100, datetime(2026, 2, 9, 11, 59, 0, tzinfo=UTC))
    validator = EventValidator(mock_saved)

    event = _make_event(stop_sequence=5, delay_seconds=0, event_time=datetime(2026, 2, 9, 12, 0, 0, tzinfo=UTC))

    assert validator.validate_event(event, "mpk", "trip_1", SERVICE_DATE) is True


# MONOTONICITY rule

def test_monotonicity_rejects_non_increasing():
    mock_saved = MagicMock()
    prev_time = datetime(2026, 2, 9, 12, 5, 0, tzinfo=UTC)
    mock_saved.get_saved_data.return_value = (30, prev_time)
    validator = EventValidator(mock_saved)

    # Current event_time is before prev_event_time
    event = _make_event(stop_sequence=5, delay_seconds=30, event_time=datetime(2026, 2, 9, 12, 4, 0, tzinfo=UTC))

    assert validator.validate_event(event, "mpk", "trip_1", SERVICE_DATE) is False


def test_monotonicity_allows_increasing():
    mock_saved = MagicMock()
    prev_time = datetime(2026, 2, 9, 12, 0, 0, tzinfo=UTC)
    mock_saved.get_saved_data.return_value = (30, prev_time)
    validator = EventValidator(mock_saved)

    event = _make_event(stop_sequence=5, delay_seconds=30, event_time=datetime(2026, 2, 9, 12, 1, 0, tzinfo=UTC))

    assert validator.validate_event(event, "mpk", "trip_1", SERVICE_DATE) is True


# No previous data

def test_validate_event_no_previous_data():
    mock_saved = MagicMock()
    mock_saved.get_saved_data.return_value = None
    validator = EventValidator(mock_saved)

    event = _make_event(stop_sequence=5, delay_seconds=30)

    assert validator.validate_event(event, "mpk", "trip_1", SERVICE_DATE) is True
