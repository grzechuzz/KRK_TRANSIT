from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.platform.db.connection import get_session


def get_db() -> Generator[Session]:
    with get_session() as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]
