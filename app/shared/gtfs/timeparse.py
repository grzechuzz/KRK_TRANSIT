from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.platform.constants import TIMEZONE


def parse_gtfs_time_to_seconds(value: str) -> int:
    """
    Returns the number of seconds since midnight of the service day.

    Note: GTFS stop_times.txt uses HH:MM:SS format where hours may exceed 24 (e.g. "25:10:00")
    """
    if value is None:
        raise ValueError("GTFS time is None")

    s = value.strip()
    parts = s.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid GTFS time format: {value!r}")

    h_str, m_str, sec_str = parts

    if not (h_str.isdigit() and m_str.isdigit() and sec_str.isdigit()):
        raise ValueError(f"Invalid GTFS time format: {value!r}")

    if len(m_str) != 2 or len(sec_str) != 2:
        raise ValueError(f"Invalid GTFS time format: {value!r}")

    h = int(h_str)
    m = int(m_str)
    sec = int(sec_str)

    if m < 0 or m > 59 or sec < 0 or sec > 59 or h < 0:
        raise ValueError(f"Invalid GTFS time value: {value!r}")

    return h * 3600 + m * 60 + sec


def compute_service_date(event_time: datetime, scheduled_seconds: int) -> date:
    """
    Compute service date.

    For overnight trips (scheduled_seconds >= 86400) date is the previous calendar day
    """
    local_time = event_time.astimezone(ZoneInfo(TIMEZONE))
    service_date = local_time.date()

    if scheduled_seconds >= 86400:
        service_date = service_date - timedelta(days=1)
    elif scheduled_seconds >= 79200 and local_time.hour < 3:
        service_date = service_date - timedelta(days=1)

    return service_date


def compute_planned_time(service_date: date, scheduled_seconds: int, tz: ZoneInfo = ZoneInfo(TIMEZONE)) -> datetime:
    """
    Converts GTFS time (seconds since service start) to actual datetime.

    e.g. 25:30:00 -> 1:30 AM next day
    """
    day_offset = scheduled_seconds // 86400
    seconds_in_day = scheduled_seconds % 86400

    base_dt = datetime(service_date.year, service_date.month, service_date.day, tzinfo=tz)

    return base_dt + timedelta(days=day_offset, seconds=seconds_in_day)


def compute_delay_seconds(event_time: datetime, planned_time: datetime) -> int:
    """
    Pretty easy to understand, I guess ;d
    """
    return int((event_time - planned_time).total_seconds())
