import time
from collections.abc import Callable, Sequence


def retry_sync[T](
    operation: Callable[[], T],
    *,
    attempts: int,
    backoff_seconds: Sequence[float],
    retriable_exceptions: tuple[type[BaseException], ...],
    on_retry: Callable[[BaseException, int, float], None] | None = None,
) -> T:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    last_exc: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except retriable_exceptions as exc:
            last_exc = exc
            if attempt >= attempts:
                break

            delay = 0.0
            if backoff_seconds:
                delay = float(backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)])

            if on_retry:
                on_retry(exc, attempt, delay)

            if delay > 0:
                time.sleep(delay)

    if last_exc is None:
        raise RuntimeError("retry_sync exhausted without capturing an exception")
    raise last_exc
