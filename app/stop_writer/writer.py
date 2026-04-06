import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.shared.models.events import StopEvent
from app.stop_writer.constants import WRITER_BATCH_SIZE, WRITER_FLUSH_INTERVAL
from app.stop_writer.repositories.stop_event import StopEventRepository

logger = logging.getLogger(__name__)


class BatchWriteError(RuntimeError):
    """Raised when buffered stop events could not be persisted."""


class BatchWriter:
    def __init__(
        self,
        session: Session,
        batch_size: int = WRITER_BATCH_SIZE,
        flush_interval: timedelta = WRITER_FLUSH_INTERVAL,
    ):
        self._session = session
        self._repo = StopEventRepository(session)
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._buffer: list[StopEvent] = []
        self._last_flush = datetime.now(UTC)

    def add_many(self, events: list[StopEvent]) -> None:
        """
        Add multiple events to buffer.
        """
        self._buffer.extend(events)

        if self._should_flush():
            self.flush()

    def flush(self) -> int:
        """
        Write buffered events to database.

        Note: Explicit commit/rollback needed because session runs in infinite loop so context manager automatic
        commit never executes.
        """
        if not self._buffer:
            return 0

        try:
            count = self._repo.insert_batch(self._buffer)
            self._session.commit()
            self._session.expire_all()
            logger.info("Wrote %d stop events", count)
            self._buffer.clear()
            self._last_flush = datetime.now(UTC)
            return count
        except Exception as e:
            logger.exception("Failed to write batch: %s", e)
            self._session.rollback()
            self._session.expire_all()
            raise BatchWriteError("Failed to persist stop event batch") from e

    def _should_flush(self) -> bool:
        if len(self._buffer) >= self._batch_size:
            return True
        if datetime.now(UTC) - self._last_flush > self._flush_interval:
            return True
        return False
