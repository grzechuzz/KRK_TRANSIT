import logging
import time

from app.rt_poller.constants import CIRCUIT_BREAKER_COOLDOWN_SECONDS, CIRCUIT_BREAKER_FAILURE_THRESHOLD

logger = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        cooldown_seconds: int = CIRCUIT_BREAKER_COOLDOWN_SECONDS,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._failures: int = 0
        self._open_until: float = 0.0

    @property
    def is_open(self) -> bool:
        return self._failures >= self._failure_threshold and time.monotonic() < self._open_until

    def record_success(self) -> None:
        if self._failures > 0:
            logger.info("Circuit closed after recovery")
        self._failures = 0
        self._open_until = 0.0

    def record_failure(self) -> bool:
        was_open = self.is_open
        self._failures += 1
        if self._failures >= self._failure_threshold:
            self._open_until = time.monotonic() + self._cooldown_seconds
            if not was_open:
                logger.warning(
                    "Circuit opened – %d consecutive failures, backing off for %ds",
                    self._failures,
                    self._cooldown_seconds,
                )
                return True
        return False
