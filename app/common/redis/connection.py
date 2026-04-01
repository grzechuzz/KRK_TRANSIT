from functools import lru_cache

import redis

from app.common.config import get_config


@lru_cache
def get_client() -> redis.Redis:
    config = get_config()
    if config.redis is None:
        raise RuntimeError("Redis is not configured (REDIS_PASSWORD not set)")

    return redis.Redis(
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db,
        username=config.redis.username,
        password=config.redis.password,
        decode_responses=False,
        socket_connect_timeout=5,
        socket_keepalive=True,
        health_check_interval=30,
    )


def ensure_available() -> None:
    client = get_client()
    if not client.ping():
        raise RuntimeError("Redis is not available")
