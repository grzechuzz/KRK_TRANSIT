from cachetools import LRUCache
from sqlalchemy.orm import Session

from app.shared.db.models import CurrentStop, CurrentStopTime, CurrentTrip
from app.shared.gtfs.repositories.gtfs_meta import GtfsMetaRepository
from app.shared.gtfs.repositories.gtfs_static import GtfsStaticRepository
from app.shared.models.enums import Agency
from app.stop_writer.constants import CACHE_MAX_SEQUENCES, CACHE_MAX_STOP_TIMES, CACHE_MAX_STOPS, CACHE_MAX_TRIPS


class GtfsCache:
    def __init__(self, session: Session):
        self._static_repo = GtfsStaticRepository(session)
        self._meta_repo = GtfsMetaRepository(session)

        self._trip_cache: LRUCache[str, CurrentTrip] = LRUCache(maxsize=CACHE_MAX_TRIPS)
        self._stop_cache: LRUCache[str, CurrentStop] = LRUCache(maxsize=CACHE_MAX_STOPS)
        self._stop_times_cache: LRUCache[str, dict[int, CurrentStopTime]] = LRUCache(maxsize=CACHE_MAX_STOP_TIMES)
        self._max_seq_cache: LRUCache[str, int] = LRUCache(maxsize=CACHE_MAX_SEQUENCES)

    def get_trip(self, trip_id: str) -> CurrentTrip | None:
        if trip_id not in self._trip_cache:
            trip = self._static_repo.get_trip(trip_id)
            if trip:
                self._trip_cache[trip_id] = trip
        return self._trip_cache.get(trip_id)

    def get_stop(self, stop_id: str) -> CurrentStop | None:
        if stop_id not in self._stop_cache:
            stop = self._static_repo.get_stop(stop_id)
            if stop:
                self._stop_cache[stop_id] = stop
        return self._stop_cache.get(stop_id)

    def get_stop_time(self, trip_id: str, stop_sequence: int) -> CurrentStopTime | None:
        if trip_id not in self._stop_times_cache:
            stop_times = self._static_repo.get_stop_times_for_trip(trip_id)
            self._stop_times_cache[trip_id] = {st.stop_sequence: st for st in stop_times}
        return self._stop_times_cache.get(trip_id, {}).get(stop_sequence)

    def get_max_stop_sequence(self, trip_id: str) -> int | None:
        if trip_id not in self._max_seq_cache:
            max_seq = self._static_repo.get_max_stop_sequence(trip_id)
            if max_seq:
                self._max_seq_cache[trip_id] = max_seq
        return self._max_seq_cache.get(trip_id)

    def get_current_hash(self, agency: Agency) -> str | None:
        return self._meta_repo.get_current_hash(agency)
