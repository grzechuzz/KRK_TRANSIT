import logging
from datetime import UTC, datetime

from google.transit import gtfs_realtime_pb2

from app.rt_poller.constants import PB_MIN_PAYLOAD_BYTES
from app.shared.gtfs.feeds import FeedConfig
from app.shared.models.enums import VehicleStatus
from app.shared.models.gtfs_realtime import StopTimeUpdate, TripUpdate, VehiclePosition

logger = logging.getLogger(__name__)


def parse_vehicle_positions(pb_data: bytes, feed: FeedConfig) -> list[VehiclePosition]:
    """
    Parse vehicle positions from VehiclePositions.pb feed.
    """
    if not pb_data or len(pb_data) < PB_MIN_PAYLOAD_BYTES:
        return []

    msg = gtfs_realtime_pb2.FeedMessage()
    try:
        msg.ParseFromString(pb_data)
    except Exception as e:
        preview = pb_data[:50].hex() if pb_data else "None"
        logger.warning("VehiclePositions %s: parse failed, data preview: %s, error: %s", feed.agency, preview, e)
        return []

    results: list[VehiclePosition] = []

    for entity in msg.entity:
        if not entity.HasField("vehicle"):
            continue

        v = entity.vehicle

        if not v.HasField("trip") or not v.trip.trip_id:
            continue

        vehicle_id = None
        license_plate = None

        if v.HasField("vehicle"):
            vehicle_id = v.vehicle.id or None
            license_plate = v.vehicle.license_plate or None

        if not license_plate:
            continue

        latitude = None
        longitude = None
        bearing = None
        if v.HasField("position"):
            latitude = v.position.latitude if v.position.HasField("latitude") else None
            longitude = v.position.longitude if v.position.HasField("longitude") else None
            bearing = v.position.bearing if v.position.HasField("bearing") else None

        stop_id = v.stop_id or None
        stop_sequence = int(v.current_stop_sequence) if v.HasField("current_stop_sequence") else None
        status = VehicleStatus.from_int(int(v.current_status)) if v.HasField("current_status") else None

        ts = v.timestamp if v.timestamp else None
        if not ts:
            continue
        timestamp = datetime.fromtimestamp(ts, tz=UTC)

        results.append(
            VehiclePosition(
                agency=feed.agency,
                trip_id=feed.prefix_id(v.trip.trip_id),
                vehicle_id=vehicle_id or "",
                license_plate=license_plate,
                latitude=latitude,
                longitude=longitude,
                bearing=bearing,
                stop_id=feed.prefix_id(stop_id) if stop_id else None,
                stop_sequence=stop_sequence,
                status=status,
                timestamp=timestamp,
            )
        )

    return results


def parse_trip_updates(pb_data: bytes, feed: FeedConfig) -> list[TripUpdate]:
    """
    Parse trip updates from TripUpdates.pb feed.
    """
    if not pb_data or len(pb_data) < PB_MIN_PAYLOAD_BYTES:
        logger.warning("TripUpdates %s: empty or too short (%d bytes)", feed.agency, len(pb_data) if pb_data else 0)
        return []

    msg = gtfs_realtime_pb2.FeedMessage()
    try:
        msg.ParseFromString(pb_data)
    except Exception as e:
        preview = pb_data[:50].hex() if pb_data else "None"
        logger.warning("TripUpdates %s: parse failed, data preview: %s, error: %s", feed.agency, preview, e)
        return []

    feed_ts = msg.header.timestamp if msg.header.timestamp else None
    fallback_timestamp = datetime.fromtimestamp(feed_ts, tz=UTC) if feed_ts else datetime.now(UTC)

    results: list[TripUpdate] = []

    for entity in msg.entity:
        if not entity.HasField("trip_update"):
            continue

        tu = entity.trip_update

        if not tu.HasField("trip") or not tu.trip.trip_id:
            continue

        vehicle_id = None
        if tu.HasField("vehicle"):
            vehicle_id = tu.vehicle.id or None

        ts = tu.timestamp if tu.timestamp else None
        timestamp = datetime.fromtimestamp(ts, tz=UTC) if ts else fallback_timestamp

        stop_time_updates: list[StopTimeUpdate] = []
        for stu in tu.stop_time_update:
            stop_id = stu.stop_id or None
            if not stop_id:
                continue

            arrival_time = None
            if stu.HasField("arrival") and stu.arrival.time:
                arrival_time = datetime.fromtimestamp(stu.arrival.time, tz=UTC)

            departure_time = None
            if stu.HasField("departure") and stu.departure.time:
                departure_time = datetime.fromtimestamp(stu.departure.time, tz=UTC)

            if arrival_time is None and departure_time is None:
                continue

            stop_time_updates.append(
                StopTimeUpdate(
                    stop_id=feed.prefix_id(stop_id),
                    stop_sequence=None,
                    arrival_time=arrival_time,
                    departure_time=departure_time,
                )
            )

        if stop_time_updates:
            results.append(
                TripUpdate(
                    agency=feed.agency,
                    trip_id=feed.prefix_id(tu.trip.trip_id),
                    vehicle_id=vehicle_id,
                    timestamp=timestamp,
                    stop_time_updates=stop_time_updates,
                )
            )

    return results
