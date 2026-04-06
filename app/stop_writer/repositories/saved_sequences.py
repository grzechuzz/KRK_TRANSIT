import logging
from datetime import date, datetime

import redis

from app.shared.redis import serializer
from app.shared.redis.schemas import SavedSequenceData
from app.stop_writer.constants import REDIS_SAVED_SEQS_TTL

logger = logging.getLogger(__name__)


class SavedSequencesRepository:
    def __init__(self, client: redis.Redis):
        self._redis = client

    @staticmethod
    def _key(agency: str, trip_id: str, service_date: date) -> str:
        return f"saved:{agency}:{trip_id}:{service_date.isoformat()}"

    def is_saved(self, agency: str, trip_id: str, service_date: date, stop_sequence: int) -> bool:
        return bool(self._redis.hexists(self._key(agency, trip_id, service_date), str(stop_sequence)))

    def get_all_sequences(self, agency: str, trip_id: str, service_date: date) -> set[int]:
        keys: list[bytes] = self._redis.hkeys(self._key(agency, trip_id, service_date))  # type: ignore[assignment]
        return {int(k) for k in keys}

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
        value = serializer.encode_saved_sequence(SavedSequenceData(delay=delay_seconds, event_time=event_time))
        pipe = self._redis.pipeline(transaction=False)
        pipe.hset(key, str(stop_sequence), value)  # type: ignore[arg-type]
        pipe.expire(key, REDIS_SAVED_SEQS_TTL)
        pipe.execute()

    def get_saved_data(
        self, agency: str, trip_id: str, service_date: date, stop_sequence: int
    ) -> tuple[int, datetime] | None:
        raw: bytes | None = self._redis.hget(self._key(agency, trip_id, service_date), str(stop_sequence))  # type: ignore[assignment]
        if not raw:
            return None
        try:
            data = serializer.decode_saved_sequence(raw)
            return data.delay, data.event_time
        except Exception:
            logger.warning(
                "Failed to decode saved sequence for trip=%s service_date=%s seq=%d",
                trip_id,
                service_date.isoformat(),
                stop_sequence,
                exc_info=True,
            )
            return None
