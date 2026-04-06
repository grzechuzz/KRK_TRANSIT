from datetime import UTC, date, datetime, timedelta

import pytest
from pytest_mock import MockerFixture

from app.shared.models.enums import Agency, DetectionMethod
from app.shared.models.events import StopEvent
from app.stop_writer.writer import BatchWriteError, BatchWriter


def _make_event(stop_sequence: int = 1) -> StopEvent:
    return StopEvent(
        agency=Agency.MPK,
        trip_id="trip_1",
        service_date=date(2026, 2, 9),
        stop_sequence=stop_sequence,
        stop_id=f"stop_{stop_sequence}",
        line_number="152",
        stop_name="Test Stop",
        stop_desc=None,
        direction_id=0,
        headsign="Dworzec",
        planned_time=datetime(2026, 2, 9, 12, 0, 0, tzinfo=UTC),
        event_time=datetime(2026, 2, 9, 12, 1, 0, tzinfo=UTC),
        delay_seconds=60,
        vehicle_id="v1",
        license_plate="AB123",
        detection_method=DetectionMethod.STOPPED_AT,
        is_estimated=False,
        static_hash="abc123",
        max_stop_sequence=10,
    )


@pytest.fixture
def mock_session(mocker: MockerFixture):
    return mocker.MagicMock()


@pytest.fixture
def writer(mock_session):
    return BatchWriter(mock_session, batch_size=5, flush_interval=timedelta(seconds=10))


def test_flush_empty_buffer_returns_zero(writer):
    assert writer.flush() == 0


def test_add_many_buffers_events(writer):
    events = [_make_event(i) for i in range(3)]

    writer.add_many(events)

    assert writer.flush() == 3


def test_flush_commits_session(writer, mock_session):
    writer.add_many([_make_event()])

    writer.flush()

    mock_session.commit.assert_called_once()


def test_flush_clears_buffer(writer):
    writer.add_many([_make_event()])

    writer.flush()

    assert writer.flush() == 0


def test_auto_flush_on_batch_size(writer, mock_session):
    events = [_make_event(i) for i in range(5)]

    writer.add_many(events)

    mock_session.commit.assert_called_once()


def test_no_auto_flush_below_batch_size(writer, mock_session):
    events = [_make_event(i) for i in range(4)]

    writer.add_many(events)

    mock_session.commit.assert_not_called()


def test_flush_rollback_on_error(writer, mock_session):
    mock_session.execute = mocker_side_effect_error(mock_session)
    writer.add_many([_make_event()])

    with pytest.raises(BatchWriteError):
        writer.flush()

    mock_session.rollback.assert_called_once()


def test_flush_keeps_buffer_on_error(writer, mock_session):
    mock_session.execute = mocker_side_effect_error(mock_session)
    writer.add_many([_make_event()])

    with pytest.raises(BatchWriteError):
        writer.flush()

    original = mock_session.execute
    original.side_effect = None

    assert writer.flush() == 1


def test_expire_all_after_commit(writer, mock_session):
    writer.add_many([_make_event()])

    writer.flush()

    mock_session.expire_all.assert_called()


def test_expire_all_after_rollback(writer, mock_session):
    mock_session.execute = mocker_side_effect_error(mock_session)
    writer.add_many([_make_event()])

    with pytest.raises(BatchWriteError):
        writer.flush()

    mock_session.expire_all.assert_called()


def mocker_side_effect_error(mock_session):
    original = mock_session.execute
    original.side_effect = Exception("DB error")
    return original
