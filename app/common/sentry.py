from collections.abc import Mapping

import sentry_sdk

from app.common.config import get_config


def setup_sentry(service_name: str, tags: Mapping[str, str] | None = None) -> None:
    config = get_config()
    if not config.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=config.sentry_dsn,
        environment=config.sentry_environment,
        traces_sample_rate=0.0,
    )

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("service", service_name)
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)


def capture_exception(exc: Exception, *, tags: Mapping[str, str] | None = None) -> None:
    if not sentry_sdk.get_client().is_active():
        return

    with sentry_sdk.push_scope() as scope:
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)
        sentry_sdk.capture_exception(exc)
