from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.api.validation import validate_date_range
from app.common.constants import TIMEZONE
from app.common.exceptions import ValidationError

_WARSAW = ZoneInfo(TIMEZONE)


def test_valid_range_passes():
    validate_date_range(date(2026, 1, 1), date(2026, 1, 31))


def test_start_after_end_raises():
    with pytest.raises(ValidationError) as exc_info:
        validate_date_range(date(2026, 2, 10), date(2026, 2, 1))

    assert exc_info.value.error_code == "VALIDATION_ERROR"
    assert "start_date must be <= end_date" in exc_info.value.message


def test_same_day_passes():
    validate_date_range(date(2026, 3, 1), date(2026, 3, 1))


def test_range_exceeds_max_days_raises():
    start = date(2025, 1, 1)
    end = start + timedelta(days=366)

    with pytest.raises(ValidationError) as exc_info:
        validate_date_range(start, end)

    assert exc_info.value.error_code == "VALIDATION_ERROR"
    assert "365" in exc_info.value.message


def test_range_exactly_max_days_passes():
    start = date(2025, 1, 1)
    end = start + timedelta(days=365)

    validate_date_range(start, end)


def test_future_end_date_raises():
    today = datetime.now(_WARSAW).date()
    future = today + timedelta(days=1)

    with pytest.raises(ValidationError) as exc_info:
        validate_date_range(today, future)

    assert exc_info.value.error_code == "VALIDATION_ERROR"
    assert "future" in exc_info.value.message


def test_today_as_end_date_passes():
    today = datetime.now(_WARSAW).date()
    validate_date_range(today, today)
