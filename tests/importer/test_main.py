import contextlib
import sys
from types import SimpleNamespace

sys.modules.setdefault(
    "sentry_sdk",
    SimpleNamespace(
        init=lambda **kwargs: None,
        configure_scope=lambda: contextlib.nullcontext(SimpleNamespace(set_tag=lambda key, value: None)),
        get_client=lambda: SimpleNamespace(is_active=lambda: False),
        push_scope=lambda: contextlib.nullcontext(SimpleNamespace(set_tag=lambda key, value: None)),
        capture_exception=lambda exc: None,
    ),
)

from app.importer.main import ImportCycleResult, _publish_import_result, run_import  # noqa: E402
from app.shared.constants import REDIS_KEY_GTFS_READY  # noqa: E402
from app.shared.gtfs.feeds import FeedConfig  # noqa: E402
from app.shared.models.enums import Agency  # noqa: E402


def _feed_config() -> FeedConfig:
    return FeedConfig(
        agency=Agency.MPK,
        static_url="https://example.test/gtfs.zip",
        static_filename="gtfs.zip",
        vehicle_positions_url="https://example.test/vehicles.pb",
        trip_updates_url="https://example.test/trips.pb",
    )


def test_publish_import_result_bumps_reload_marker_on_partial_success(mocker):
    redis = mocker.MagicMock()
    bump_reload_marker = mocker.patch("app.importer.main.bump_reload_marker", return_value=b"marker")

    _publish_import_result(ImportCycleResult(all_ok=False, any_changed=True), redis)

    redis.set.assert_not_called()
    bump_reload_marker.assert_called_once_with(redis)


def test_publish_import_result_sets_ready_when_all_feeds_ok(mocker):
    redis = mocker.MagicMock()
    bump_reload_marker = mocker.patch("app.importer.main.bump_reload_marker")

    _publish_import_result(ImportCycleResult(all_ok=True, any_changed=False), redis)

    redis.set.assert_called_once_with(REDIS_KEY_GTFS_READY, "1")
    bump_reload_marker.assert_not_called()


def test_run_import_removes_downloaded_zip_after_failure(tmp_path, mocker):
    zip_path = tmp_path / "feed.zip"
    zip_path.write_bytes(b"invalid feed")

    mocker.patch("app.importer.main.get_all_feed_configs", return_value=[_feed_config()])
    mocker.patch("app.importer.main.download_gtfs_zip", return_value=zip_path)
    mocker.patch("app.importer.main.sha256_file", side_effect=RuntimeError("hash failed"))
    mocker.patch("app.importer.main.capture_exception")

    result = run_import()

    assert result.all_ok is False
    assert result.any_changed is False
    assert not zip_path.exists()
