import time
from typing import cast

import redis

from app.shared.constants import REDIS_KEY_GTFS_RELOAD_MARKER


class ReloadRequiredError(RuntimeError):
    """Raised when GTFS static data changed and the process should restart."""


def get_reload_marker(redis_client: redis.Redis) -> bytes | None:
    return cast(bytes | None, redis_client.get(REDIS_KEY_GTFS_RELOAD_MARKER))


def bump_reload_marker(redis_client: redis.Redis) -> bytes:
    marker = str(time.time_ns()).encode()
    redis_client.set(REDIS_KEY_GTFS_RELOAD_MARKER, marker)
    return marker


class ReloadWatcher:
    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client
        self._initial_marker = get_reload_marker(redis_client)

    def raise_if_changed(self) -> None:
        marker = get_reload_marker(self._redis)
        if marker is not None and marker != self._initial_marker:
            raise ReloadRequiredError("GTFS reload marker changed")
