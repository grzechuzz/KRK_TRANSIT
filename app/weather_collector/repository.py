from datetime import datetime
from typing import Any, cast

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.common.db.models import WeatherObservation


class WeatherRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_latest_observed_at(self) -> datetime | None:
        result = (
            self._session.query(WeatherObservation.observed_at).order_by(WeatherObservation.observed_at.desc()).first()
        )
        return result[0] if result else None

    def upsert_observations(self, observations: list[WeatherObservation]) -> int:
        if not observations:
            return 0
        stmt = (
            insert(WeatherObservation)
            .values(
                [
                    {
                        "observed_at": o.observed_at,
                        "temperature_c": o.temperature_c,
                        "precipitation_mm": o.precipitation_mm,
                        "rain_mm": o.rain_mm,
                        "snowfall_cm": o.snowfall_cm,
                        "snow_depth_cm": o.snow_depth_cm,
                        "wind_speed_kmh": o.wind_speed_kmh,
                        "wind_gusts_kmh": o.wind_gusts_kmh,
                        "cloud_cover_pct": o.cloud_cover_pct,
                        "visibility_m": o.visibility_m,
                        "is_day": o.is_day,
                        "weather_code": o.weather_code,
                    }
                    for o in observations
                ]
            )
            .on_conflict_do_nothing(index_elements=["observed_at"])
        )
        result: CursorResult[Any] = cast(CursorResult[Any], self._session.execute(stmt))
        return result.rowcount
