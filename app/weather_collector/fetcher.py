import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from app.platform.constants import TIMEZONE, USER_AGENT
from app.platform.retry import retry_sync
from app.shared.db.models import WeatherObservation
from app.weather_collector.constants import (
    WEATHER_FETCH_MAX_RETRIES,
    WEATHER_FETCH_RETRY_BACKOFF_SECONDS,
    WEATHER_FETCH_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_KRAKOW_LAT = 50.06
_KRAKOW_LON = 19.94
_HOURLY_VARS = (
    "temperature_2m,"
    "precipitation,"
    "rain,"
    "snowfall,"
    "snow_depth,"
    "wind_speed_10m,"
    "wind_gusts_10m,"
    "cloud_cover,"
    "visibility,"
    "is_day,"
    "weather_code"
)


def fetch_weather(past_days: int) -> list[WeatherObservation]:
    """Fetch hourly weather from Open-Meteo for Kraków. Retries up to 3 times on failure."""
    params: dict[str, str | int | float] = {
        "latitude": _KRAKOW_LAT,
        "longitude": _KRAKOW_LON,
        "hourly": _HOURLY_VARS,
        "timezone": TIMEZONE,
        "past_days": past_days,
        "forecast_days": 0,
    }
    response = retry_sync(
        lambda: requests.get(
            _OPEN_METEO_URL,
            params=params,
            timeout=WEATHER_FETCH_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        ),
        attempts=WEATHER_FETCH_MAX_RETRIES,
        backoff_seconds=WEATHER_FETCH_RETRY_BACKOFF_SECONDS,
        retriable_exceptions=(requests.RequestException,),
        on_retry=lambda exc, attempt, delay: logger.warning(
            "Open-Meteo fetch failed on attempt %d: %s. Retrying in %ss",
            attempt,
            exc,
            int(delay),
        ),
    )
    response.raise_for_status()
    data = response.json()

    tz = ZoneInfo(TIMEZONE)
    h = data["hourly"]

    now_local = datetime.now(tz)

    observations: list[WeatherObservation] = []
    for i, time_str in enumerate(h["time"]):
        if h["temperature_2m"][i] is None:
            continue

        observed_time = datetime.fromisoformat(time_str).replace(tzinfo=tz)

        if observed_time > now_local:
            continue

        observations.append(
            WeatherObservation(
                observed_at=observed_time,
                temperature_c=h["temperature_2m"][i],
                precipitation_mm=h["precipitation"][i] or 0.0,
                rain_mm=h["rain"][i] or 0.0,
                snowfall_cm=h["snowfall"][i] or 0.0,
                snow_depth_cm=h["snow_depth"][i] or 0.0,
                wind_speed_kmh=h["wind_speed_10m"][i] or 0.0,
                wind_gusts_kmh=h["wind_gusts_10m"][i] or 0.0,
                cloud_cover_pct=h["cloud_cover"][i] or 0,
                visibility_m=h["visibility"][i] or 0.0,
                is_day=bool(h["is_day"][i]),
                weather_code=h["weather_code"][i] or 0,
            )
        )

    return observations
