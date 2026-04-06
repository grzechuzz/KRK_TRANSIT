from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.shared.db.models import GtfsMeta
from app.shared.models.enums import Agency


class GtfsMetaRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_current_hash(self, agency: Agency) -> str | None:
        meta = self._session.get(GtfsMeta, agency.value)
        return meta.current_hash if meta else None

    def set_current_hash(self, agency: Agency, hash_value: str) -> None:
        meta = self._session.get(GtfsMeta, agency.value)

        if meta:
            meta.current_hash = hash_value
            meta.updated_at = datetime.now(UTC)
        else:
            meta = GtfsMeta(agency=agency.value, current_hash=hash_value)
            self._session.add(meta)
