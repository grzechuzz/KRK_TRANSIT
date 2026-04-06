import logging
from datetime import date

import msgspec
import redis

from app.api.constants import (
    DEFAULT_TTL,
    LONG_TTL,
    LONG_TTL_THRESHOLD_DAYS,
    REDIS_KEY_VEHICLES_CACHE,
    VEHICLES_CACHE_TTL,
)
from app.platform.redis.connection import get_client

logger = logging.getLogger(__name__)


def _ttl(start_date: date, end_date: date) -> int:
    span = (end_date - start_date).days
    return LONG_TTL if span >= LONG_TTL_THRESHOLD_DAYS else DEFAULT_TTL


def _key(endpoint: str, line_number: str, start_date: date, end_date: date, include_estimated: bool = False) -> str:
    suffix = ":est" if include_estimated else ""
    return f"stats:{endpoint}:{line_number}:{start_date}:{end_date}{suffix}"


def get_cached(
    endpoint: str, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
) -> bytes | None:
    try:
        client = get_client()
        return client.get(_key(endpoint, line_number, start_date, end_date, include_estimated))  # type: ignore
    except redis.RedisError:
        logger.warning("Redis read failed for stats cache", exc_info=True)
        return None


def set_cached(
    endpoint: str,
    line_number: str,
    start_date: date,
    end_date: date,
    data: msgspec.Struct,
    include_estimated: bool = False,
) -> None:
    raw = msgspec.json.encode(data)
    try:
        client = get_client()
        client.setex(
            _key(endpoint, line_number, start_date, end_date, include_estimated), _ttl(start_date, end_date), raw
        )
    except redis.RedisError:
        logger.warning("Redis write failed for stats cache", exc_info=True)


def get_vehicles_cache() -> bytes | None:
    try:
        client = get_client()
        return client.get(REDIS_KEY_VEHICLES_CACHE)  # type: ignore
    except redis.RedisError:
        logger.warning("Redis read failed for vehicles cache", exc_info=True)
        return None


def set_vehicles_cache(data: bytes) -> None:
    try:
        client = get_client()
        client.setex(REDIS_KEY_VEHICLES_CACHE, VEHICLES_CACHE_TTL, data)
    except redis.RedisError:
        logger.warning("Redis write failed for vehicles cache", exc_info=True)
