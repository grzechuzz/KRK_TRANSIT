from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from app.shared.db.models import CurrentRoute, CurrentStop, CurrentStopTime, CurrentTrip
from app.shared.models.enums import Agency, VehicleStatus
from app.shared.models.gtfs_realtime import VehiclePosition
from app.shared.redis.schemas import CachedStopTime, TripUpdateCache, VehicleState
from app.stop_writer.detector import StopEventDetector
from app.stop_writer.detector.gtfs_cache import GtfsCache


def make_vehicle_position(
    trip_id: str = "trip_1",
    stop_sequence: int | None = 5,
    status: VehicleStatus | None = VehicleStatus.STOPPED_AT,
    license_plate: str | None = "AB123",
    timestamp: datetime | None = None,
    agency: Agency = Agency.MPK,
) -> VehiclePosition:
    return VehiclePosition(
        agency=agency,
        trip_id=trip_id,
        vehicle_id="v1",
        license_plate=license_plate,
        latitude=50.06,
        longitude=19.94,
        bearing=None,
        stop_id=f"stop_{stop_sequence}",
        stop_sequence=stop_sequence,
        status=status,
        timestamp=timestamp or datetime(2026, 2, 9, 12, 0, 0, tzinfo=UTC),
    )


def make_vehicle_state(
    trip_id: str = "trip_1",
    stop_sequence: int = 3,
    license_plate: str = "AB123",
    agency: str = "mpk",
    timestamp: datetime | None = None,
) -> VehicleState:
    return VehicleState(
        agency=agency,
        license_plate=license_plate,
        trip_id=trip_id,
        current_stop_sequence=stop_sequence,
        last_timestamp=timestamp or datetime(2026, 2, 9, 11, 58, 0, tzinfo=UTC),
    )


def make_trip(trip_id: str = "trip_1", route_short_name: str = "152", agency_id: str = "mpk") -> CurrentTrip:
    route = CurrentRoute()
    route.route_id = "route_1"
    route.agency_id = agency_id
    route.route_short_name = route_short_name

    trip = CurrentTrip()
    trip.trip_id = trip_id
    trip.route_id = "route_1"
    trip.agency_id = agency_id
    trip.service_id = "service_1"
    trip.direction_id = 0
    trip.headsign = "Dworzec Główny"
    trip.shape_id = None
    trip.route = route
    return trip


def make_stop(stop_id: str = "stop_5", stop_name: str = "Rondo Mogilskie", agency_id: str = "mpk") -> CurrentStop:
    stop = CurrentStop()
    stop.stop_id = stop_id
    stop.agency_id = agency_id
    stop.stop_name = stop_name
    stop.stop_code = None
    stop.stop_desc = "01"
    stop.stop_lat = 50.06
    stop.stop_lon = 19.94
    return stop


def make_stop_time(
    trip_id: str = "trip_1",
    stop_sequence: int = 5,
    stop_id: str | None = None,
    arrival_seconds: int = 43200,
    agency_id: str = "mpk",
) -> CurrentStopTime:
    st = CurrentStopTime()
    st.trip_id = trip_id
    st.stop_sequence = stop_sequence
    st.stop_id = stop_id or f"stop_{stop_sequence}"
    st.agency_id = agency_id
    st.arrival_seconds = arrival_seconds
    st.departure_seconds = arrival_seconds + 30
    return st


def make_trip_update_cache(
    trip_id: str = "trip_1",
    stops: dict[int, tuple[datetime, datetime]] | None = None,
    agency: str = "mpk",
) -> TripUpdateCache:
    cached_stops: dict[int, CachedStopTime] = {}
    if stops:
        for seq, (first, last) in stops.items():
            cached_stops[seq] = CachedStopTime(
                stop_id=f"stop_{seq}",
                stop_sequence=seq,
                first_seen_arrival=first,
                last_seen_arrival=last,
            )
    return TripUpdateCache(
        agency=agency,
        trip_id=trip_id,
        stops=cached_stops,
    )


@pytest.fixture
def mock_vehicle_state(mocker: MockerFixture):
    mock = mocker.MagicMock()
    mock.get.return_value = None
    return mock


@pytest.fixture
def mock_trip_updates(mocker: MockerFixture):
    mock = mocker.MagicMock()
    mock.get.return_value = None
    mock.get_arrival.return_value = None
    return mock


@pytest.fixture
def mock_saved_seqs(mocker: MockerFixture):
    mock = mocker.MagicMock()
    mock.is_saved.return_value = False
    mock.get_all_sequences.return_value = set()
    mock.get_saved_data.return_value = None
    return mock


@pytest.fixture
def detector(mocker: MockerFixture, mock_vehicle_state, mock_trip_updates, mock_saved_seqs):
    mocker.patch.object(GtfsCache, "get_trip", return_value=make_trip())
    mocker.patch.object(GtfsCache, "get_stop", return_value=make_stop())
    mocker.patch.object(
        GtfsCache,
        "get_stop_time",
        side_effect=lambda tid, seq: make_stop_time(trip_id=tid, stop_sequence=seq),
    )
    mocker.patch.object(GtfsCache, "get_max_stop_sequence", return_value=10)
    mocker.patch.object(GtfsCache, "get_current_hash", return_value="abc123hash")

    return StopEventDetector(
        session=mocker.MagicMock(),
        redis_vehicle_state=mock_vehicle_state,
        redis_trip_updates=mock_trip_updates,
        redis_saved_seqs=mock_saved_seqs,
    )
