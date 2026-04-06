import requests

from app.platform.constants import USER_AGENT
from app.platform.retry import retry_sync
from app.rt_poller.constants import (
    RT_FETCH_RETRY_ATTEMPTS,
    RT_FETCH_RETRY_BACKOFF_SECONDS,
    RT_FETCH_TIMEOUT_SECONDS,
)
from app.shared.gtfs.feeds import FeedConfig

_HEADERS = {"User-Agent": USER_AGENT}


def fetch_vehicle_positions(feed: FeedConfig, timeout: int = RT_FETCH_TIMEOUT_SECONDS) -> bytes:
    """Fetch VehiclePositions.pb feed."""
    response = retry_sync(
        lambda: requests.get(feed.vehicle_positions_url, timeout=timeout, headers=_HEADERS),
        attempts=RT_FETCH_RETRY_ATTEMPTS,
        backoff_seconds=RT_FETCH_RETRY_BACKOFF_SECONDS,
        retriable_exceptions=(requests.RequestException,),
    )
    response.raise_for_status()
    return response.content


def fetch_trip_updates(feed: FeedConfig, timeout: int = RT_FETCH_TIMEOUT_SECONDS) -> bytes:
    """Fetch TripUpdates.pb feed."""
    response = retry_sync(
        lambda: requests.get(feed.trip_updates_url, timeout=timeout, headers=_HEADERS),
        attempts=RT_FETCH_RETRY_ATTEMPTS,
        backoff_seconds=RT_FETCH_RETRY_BACKOFF_SECONDS,
        retriable_exceptions=(requests.RequestException,),
    )
    response.raise_for_status()
    return response.content
