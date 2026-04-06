import pytest

from app.platform.retry import retry_sync


def test_retry_sync_returns_after_retry() -> None:
    attempts = 0

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("transient")
        return "ok"

    seen: list[tuple[int, float]] = []
    result = retry_sync(
        operation,
        attempts=3,
        backoff_seconds=[0, 0],
        retriable_exceptions=(ValueError,),
        on_retry=lambda _exc, attempt, delay: seen.append((attempt, delay)),
    )

    assert result == "ok"
    assert attempts == 3
    assert seen == [(1, 0.0), (2, 0.0)]


def test_retry_sync_raises_after_exhausting_attempts() -> None:
    attempts = 0

    def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise ValueError("still broken")

    with pytest.raises(ValueError, match="still broken"):
        retry_sync(
            operation,
            attempts=3,
            backoff_seconds=[0, 0],
            retriable_exceptions=(ValueError,),
        )

    assert attempts == 3


def test_retry_sync_does_not_retry_non_retriable_exception() -> None:
    attempts = 0

    def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise TypeError("fatal")

    with pytest.raises(TypeError, match="fatal"):
        retry_sync(
            operation,
            attempts=3,
            backoff_seconds=[0, 0],
            retriable_exceptions=(ValueError,),
        )

    assert attempts == 1
