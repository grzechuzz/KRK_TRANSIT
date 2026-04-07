import pytest

from app.shared.constants import REDIS_KEY_GTFS_RELOAD_MARKER
from app.shared.gtfs.reload_marker import ReloadRequiredError, ReloadWatcher, bump_reload_marker, get_reload_marker


class FakeRedis:
    def __init__(self):
        self._values: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self._values.get(key)

    def set(self, key: str, value: bytes) -> None:
        self._values[key] = value


def test_bump_reload_marker_stores_new_marker():
    redis = FakeRedis()

    marker = bump_reload_marker(redis)  # type: ignore[arg-type]

    assert marker == get_reload_marker(redis)  # type: ignore[arg-type]
    assert redis.get(REDIS_KEY_GTFS_RELOAD_MARKER) == marker


def test_reload_watcher_does_not_raise_when_marker_unchanged():
    redis = FakeRedis()
    redis.set(REDIS_KEY_GTFS_RELOAD_MARKER, b"123")
    watcher = ReloadWatcher(redis)  # type: ignore[arg-type]

    watcher.raise_if_changed()


def test_reload_watcher_raises_when_marker_changes():
    redis = FakeRedis()
    redis.set(REDIS_KEY_GTFS_RELOAD_MARKER, b"123")
    watcher = ReloadWatcher(redis)  # type: ignore[arg-type]
    redis.set(REDIS_KEY_GTFS_RELOAD_MARKER, b"456")

    with pytest.raises(ReloadRequiredError):
        watcher.raise_if_changed()
