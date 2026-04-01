from datetime import UTC, datetime

from app.common.models.enums import Agency, DetectionMethod, VehicleStatus

from conftest import make_trip_update_cache, make_vehicle_position, make_vehicle_state


# STOPPED_AT DETECTION

def test_stopped_at_creates_event(detector):
    vp = make_vehicle_position(status=VehicleStatus.STOPPED_AT, stop_sequence=5)

    events = detector.process_update(vp)

    assert len(events) == 1
    assert events[0].detection_method == DetectionMethod.STOPPED_AT
    assert events[0].stop_sequence == 5
    assert events[0].is_estimated is False


def test_stopped_at_skips_already_saved(detector, mock_saved_seqs):
    mock_saved_seqs.is_saved.return_value = True
    vp = make_vehicle_position(status=VehicleStatus.STOPPED_AT, stop_sequence=5)

    events = detector.process_update(vp)

    assert len(events) == 0


def test_stopped_at_marks_saved(detector, mock_saved_seqs):
    vp = make_vehicle_position(status=VehicleStatus.STOPPED_AT, stop_sequence=5)

    detector.process_update(vp)

    mock_saved_seqs.mark_saved.assert_called_once()


def test_in_transit_no_event(detector):
    vp = make_vehicle_position(status=VehicleStatus.IN_TRANSIT_TO, stop_sequence=5)

    events = detector.process_update(vp)

    assert len(events) == 0


def test_incoming_at_no_event(detector):
    vp = make_vehicle_position(status=VehicleStatus.INCOMING_AT, stop_sequence=5)

    events = detector.process_update(vp)

    assert len(events) == 0


# SEQ_JUMP detection

def test_seq_jump_detects_missed_stops(detector, mock_vehicle_state, mock_trip_updates):
    mock_vehicle_state.get.return_value = make_vehicle_state(trip_id="trip_1", stop_sequence=3)

    cached_time = datetime(2026, 2, 9, 11, 59, 0, tzinfo=UTC)
    mock_trip_updates.get.return_value = make_trip_update_cache(
        trip_id="trip_1",
        stops={3: (cached_time, cached_time), 4: (cached_time, cached_time)},
    )

    vp = make_vehicle_position(status=VehicleStatus.IN_TRANSIT_TO, stop_sequence=5)

    events = detector.process_update(vp)

    seq_jump_events = [e for e in events if e.detection_method == DetectionMethod.SEQ_JUMP]
    assert len(seq_jump_events) == 2
    assert {e.stop_sequence for e in seq_jump_events} == {3, 4}
    assert all(e.is_estimated is True for e in seq_jump_events)


def test_seq_jump_skips_saved(detector, mock_vehicle_state, mock_trip_updates, mock_saved_seqs):
    mock_vehicle_state.get.return_value = make_vehicle_state(trip_id="trip_1", stop_sequence=3)

    cached_time = datetime(2026, 2, 9, 11, 59, 0, tzinfo=UTC)
    mock_trip_updates.get.return_value = make_trip_update_cache(
        trip_id="trip_1",
        stops={3: (cached_time, cached_time), 4: (cached_time, cached_time)},
    )
    mock_saved_seqs.get_all_sequences.return_value = {3}

    vp = make_vehicle_position(status=VehicleStatus.IN_TRANSIT_TO, stop_sequence=5)

    events = detector.process_update(vp)

    seq_jump_events = [e for e in events if e.detection_method == DetectionMethod.SEQ_JUMP]
    assert len(seq_jump_events) == 1
    assert seq_jump_events[0].stop_sequence == 4


def test_seq_jump_skips_no_cached_time(detector, mock_vehicle_state, mock_trip_updates):
    mock_vehicle_state.get.return_value = make_vehicle_state(trip_id="trip_1", stop_sequence=3)
    mock_trip_updates.get.return_value = None

    vp = make_vehicle_position(status=VehicleStatus.IN_TRANSIT_TO, stop_sequence=5)

    events = detector.process_update(vp)

    assert len(events) == 0


def test_no_jump_same_sequence(detector, mock_vehicle_state):
    mock_vehicle_state.get.return_value = make_vehicle_state(trip_id="trip_1", stop_sequence=5)

    vp = make_vehicle_position(status=VehicleStatus.IN_TRANSIT_TO, stop_sequence=5)

    events = detector.process_update(vp)

    assert len(events) == 0


def test_no_jump_sequence_decreases(detector, mock_vehicle_state):
    mock_vehicle_state.get.return_value = make_vehicle_state(trip_id="trip_1", stop_sequence=5)

    vp = make_vehicle_position(status=VehicleStatus.IN_TRANSIT_TO, stop_sequence=3)

    events = detector.process_update(vp)

    assert len(events) == 0


# Trip completion (TIMEOUT)

def test_trip_change_completes_previous(detector, mock_vehicle_state, mock_trip_updates):
    mock_vehicle_state.get.return_value = make_vehicle_state(trip_id="trip_1", stop_sequence=8)

    t9 = datetime(2026, 2, 9, 12, 5, 0, tzinfo=UTC)
    t10 = datetime(2026, 2, 9, 12, 8, 0, tzinfo=UTC)
    mock_trip_updates.get.return_value = make_trip_update_cache(
        trip_id="trip_1",
        stops={9: (t9, t9), 10: (t10, t10)},
    )

    vp = make_vehicle_position(trip_id="trip_2", status=VehicleStatus.STOPPED_AT, stop_sequence=1)

    events = detector.process_update(vp)

    completion_events = [e for e in events if e.trip_id == "trip_1"]
    assert len(completion_events) == 2
    assert {e.stop_sequence for e in completion_events} == {9, 10}


def test_last_stop_uses_first_seen_arrival(detector, mock_vehicle_state, mock_trip_updates):
    mock_vehicle_state.get.return_value = make_vehicle_state(trip_id="trip_1", stop_sequence=9)

    first_seen = datetime(2026, 2, 9, 12, 5, 0, tzinfo=UTC)
    last_seen = datetime(2026, 2, 9, 12, 8, 0, tzinfo=UTC)
    mock_trip_updates.get.return_value = make_trip_update_cache(
        trip_id="trip_1",
        stops={10: (first_seen, last_seen)},
    )

    vp = make_vehicle_position(trip_id="trip_2", status=VehicleStatus.IN_TRANSIT_TO, stop_sequence=1)

    events = detector.process_update(vp)

    timeout_events = [e for e in events if e.detection_method == DetectionMethod.TIMEOUT]
    assert len(timeout_events) == 1
    assert timeout_events[0].event_time == first_seen


def test_non_last_stop_uses_last_seen_arrival(detector, mock_vehicle_state, mock_trip_updates):
    mock_vehicle_state.get.return_value = make_vehicle_state(trip_id="trip_1", stop_sequence=7)

    first_seen = datetime(2026, 2, 9, 12, 3, 0, tzinfo=UTC)
    last_seen = datetime(2026, 2, 9, 12, 5, 0, tzinfo=UTC)
    t10 = datetime(2026, 2, 9, 12, 10, 0, tzinfo=UTC)
    mock_trip_updates.get.return_value = make_trip_update_cache(
        trip_id="trip_1",
        stops={8: (first_seen, last_seen), 9: (first_seen, last_seen), 10: (t10, t10)},
    )

    vp = make_vehicle_position(trip_id="trip_2", status=VehicleStatus.IN_TRANSIT_TO, stop_sequence=1)

    events = detector.process_update(vp)

    seq_jump_events = [e for e in events if e.detection_method == DetectionMethod.SEQ_JUMP]
    for event in seq_jump_events:
        assert event.event_time == last_seen


def test_trip_completion_cleans_redis(detector, mock_vehicle_state, mock_trip_updates):
    mock_vehicle_state.get.return_value = make_vehicle_state(trip_id="trip_1", stop_sequence=9)
    mock_trip_updates.get.return_value = None

    vp = make_vehicle_position(trip_id="trip_2", status=VehicleStatus.IN_TRANSIT_TO, stop_sequence=1)

    detector.process_update(vp)

    mock_trip_updates.delete.assert_called_with("mpk", "trip_1")
    mock_vehicle_state.delete.assert_called_with("mpk", "AB123")


# Edge cases

def test_no_stop_sequence_returns_empty(detector):
    vp = make_vehicle_position(stop_sequence=None)

    assert detector.process_update(vp) == []


def test_no_license_plate_returns_empty(detector):
    vp = make_vehicle_position(license_plate=None)

    assert detector.process_update(vp) == []


def test_saves_vehicle_state(detector, mock_vehicle_state):
    vp = make_vehicle_position(status=VehicleStatus.IN_TRANSIT_TO, stop_sequence=5)

    detector.process_update(vp)

    mock_vehicle_state.save.assert_called_once()
    saved = mock_vehicle_state.save.call_args[0][0]
    assert saved.trip_id == "trip_1"
    assert saved.current_stop_sequence == 5


def test_event_has_correct_line_and_agency(detector):
    vp = make_vehicle_position(status=VehicleStatus.STOPPED_AT, stop_sequence=5, agency=Agency.MPK)

    events = detector.process_update(vp)

    assert events[0].line_number == "152"
    assert events[0].agency == Agency.MPK


def test_stopped_at_plus_seq_jump_combined(detector, mock_vehicle_state, mock_trip_updates):
    mock_vehicle_state.get.return_value = make_vehicle_state(trip_id="trip_1", stop_sequence=3)

    cached_time = datetime(2026, 2, 9, 11, 59, 0, tzinfo=UTC)
    mock_trip_updates.get.return_value = make_trip_update_cache(
        trip_id="trip_1",
        stops={3: (cached_time, cached_time), 4: (cached_time, cached_time)},
    )

    vp = make_vehicle_position(status=VehicleStatus.STOPPED_AT, stop_sequence=5)

    events = detector.process_update(vp)

    methods = {e.detection_method for e in events}
    assert DetectionMethod.STOPPED_AT in methods
    assert DetectionMethod.SEQ_JUMP in methods
    assert len(events) == 3  # stops 3, 4 (SEQ_JUMP) + stop 5 (STOPPED_AT)
