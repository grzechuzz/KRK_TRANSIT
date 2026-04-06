import logging
from datetime import UTC, datetime

import redis

from app.shared.models.gtfs_realtime import TripUpdate
from app.shared.redis import serializer
from app.shared.redis.constants import REDIS_TRIP_UPDATES_TTL
from app.shared.redis.schemas import CachedStopTime, TripUpdateCache

logger = logging.getLogger(__name__)


class TripUpdatesRepository:
    def __init__(self, client: redis.Redis):
        self._redis = client

    @staticmethod
    def _key(agency: str, trip_id: str) -> str:
        return f"tu:{agency}:{trip_id}"

    def get(self, agency: str, trip_id: str) -> TripUpdateCache | None:
        data: bytes | None = self._redis.get(self._key(agency, trip_id))  # type: ignore[assignment]
        if data is None:
            return None
        try:
            return serializer.decode_trip_update(data)
        except Exception:
            logger.warning("Failed to decode trip updates cache entry for trip=%s", trip_id, exc_info=True)
            return None

    def update(self, trip_update: TripUpdate, stop_id_to_seq: dict[str, int]) -> None:
        agency = trip_update.agency.value
        trip_id = trip_update.trip_id
        key = self._key(agency, trip_id)
        now = datetime.now(UTC)

        existing = self.get(agency, trip_id)
        existing_stops = existing.stops if existing else {}

        incoming_seqs = []
        for stu in trip_update.stop_time_updates:
            seq = stu.stop_sequence or stop_id_to_seq.get(stu.stop_id)
            if seq is not None:
                incoming_seqs.append(seq)

        incoming_min_seq = min(incoming_seqs) if incoming_seqs else None
        prev_min_seq = existing.last_min_seq if existing else None
        vehicle_moved = incoming_min_seq is not None and prev_min_seq is not None and incoming_min_seq > prev_min_seq

        new_stops: dict[int, CachedStopTime] = dict(existing_stops)

        for stu in trip_update.stop_time_updates:
            stop_seq = stu.stop_sequence or stop_id_to_seq.get(stu.stop_id)
            if stop_seq is None:
                continue

            arrival = stu.arrival_time or stu.departure_time
            if arrival is None:
                continue

            if stop_seq in new_stops and not vehicle_moved:
                old = new_stops[stop_seq]
                new_stops[stop_seq] = CachedStopTime(
                    stop_id=stu.stop_id,
                    stop_sequence=stop_seq,
                    first_seen_arrival=old.first_seen_arrival,
                    last_seen_arrival=arrival,
                )
            else:
                new_stops[stop_seq] = CachedStopTime(
                    stop_id=stu.stop_id,
                    stop_sequence=stop_seq,
                    first_seen_arrival=arrival,
                    last_seen_arrival=arrival,
                )

        cache = TripUpdateCache(
            agency=agency,
            trip_id=trip_id,
            stops=new_stops,
            created_at=existing.created_at if existing else now,
            last_min_seq=incoming_min_seq or prev_min_seq,
        )
        self._redis.setex(key, REDIS_TRIP_UPDATES_TTL, serializer.encode(cache))

    def delete(self, agency: str, trip_id: str) -> None:
        self._redis.delete(self._key(agency, trip_id))

    def get_arrival(self, agency: str, trip_id: str, stop_sequence: int) -> datetime | None:
        """Get last seen arrival time for a stop."""
        cache = self.get(agency, trip_id)
        if cache is None:
            return None

        cached = cache.stops.get(stop_sequence)
        if cached is None:
            return None

        return cached.last_seen_arrival
