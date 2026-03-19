import json
from datetime import date, datetime

import redis

from app.common.constants import REDIS_SAVED_SEQS_TTL


class SavedSequencesRepository:
    def __init__(self, client: redis.Redis):
        self._redis = client

    @staticmethod
    def _key(agency: str, trip_id: str, service_date: date) -> str:
        return f"saved:{agency}:{trip_id}:{service_date.isoformat()}"

    def is_saved(self, agency: str, trip_id: str, service_date: date, stop_sequence: int) -> bool:
        return bool(self._redis.hexists(self._key(agency, trip_id, service_date), str(stop_sequence)))

    def mark_saved(
        self,
        agency: str,
        trip_id: str,
        service_date: date,
        stop_sequence: int,
        delay_seconds: int,
        event_time: datetime,
    ) -> None:
        key = self._key(agency, trip_id, service_date)
        value = json.dumps({"delay": delay_seconds, "event_time": event_time.isoformat()})
        self._redis.hset(key, str(stop_sequence), value)
        self._redis.expire(key, REDIS_SAVED_SEQS_TTL)

    def get_saved_data(
        self, agency: str, trip_id: str, service_date: date, stop_sequence: int
    ) -> tuple[int, datetime] | None:
        raw: bytes | None = self._redis.hget(self._key(agency, trip_id, service_date), str(stop_sequence))  # type: ignore[assignment]
        if not raw:
            return None
        data = json.loads(raw)
        return data["delay"], datetime.fromisoformat(data["event_time"])
