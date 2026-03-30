import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from app.common.constants import (
    TIMEZONE,
    USER_AGENT,
    WEATHER_FETCH_MAX_RETRIES,
    WEATHER_FETCH_RETRY_BACKOFF_SECONDS,
    WEATHER_FETCH_TIMEOUT_SECONDS,
)
from app.common.db.models import WeatherObservation

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
    params = {
        "latitude": _KRAKOW_LAT,
        "longitude": _KRAKOW_LON,
        "hourly": _HOURLY_VARS,
        "timezone": TIMEZONE,
        "past_days": past_days,
        "forecast_days": 1,
    }
    last_exc: Exception = RuntimeError("no attempts made")
    for attempt, backoff in enumerate(WEATHER_FETCH_RETRY_BACKOFF_SECONDS, start=1):
        try:
            response = requests.get(
                _OPEN_METEO_URL,
                params=params,
                timeout=WEATHER_FETCH_TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            data = response.json()
            break
        except Exception as e:
            last_exc = e
            if attempt < WEATHER_FETCH_MAX_RETRIES:
                logger.warning(
                    f"Open-Meteo fetch failed (attempt {attempt}/{_MAX_RETRIES}): {e}, retrying in {backoff}s"
                )
                time.sleep(backoff)
    else:
        raise last_exc

    tz = ZoneInfo(TIMEZONE)
    h = data["hourly"]

    observations: list[WeatherObservation] = []
    for i, time_str in enumerate(h["time"]):
        if h["temperature_2m"][i] is None:
            continue
        observations.append(
            WeatherObservation(
                observed_at=datetime.fromisoformat(time_str).replace(tzinfo=tz),
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
