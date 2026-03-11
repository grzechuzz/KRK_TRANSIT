from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.api.validation import validate_date_range


def test_valid_range_passes():
    validate_date_range(date(2026, 1, 1), date(2026, 1, 31))


def test_start_after_end_raises():
    with pytest.raises(HTTPException) as exc_info:
        validate_date_range(date(2026, 2, 10), date(2026, 2, 1))

    assert exc_info.value.status_code == 422
    assert "start_date must be <= end_date" in exc_info.value.detail


def test_same_day_passes():
    validate_date_range(date(2026, 3, 1), date(2026, 3, 1))


def test_range_exceeds_max_days_raises():
    start = date(2025, 1, 1)
    end = start + timedelta(days=366)

    with pytest.raises(HTTPException) as exc_info:
        validate_date_range(start, end)

    assert exc_info.value.status_code == 422
    assert "365" in exc_info.value.detail


def test_range_exactly_max_days_passes():
    start = date(2025, 1, 1)
    end = start + timedelta(days=365)

    validate_date_range(start, end)


def test_future_end_date_raises():
    today = date.today()
    future = today + timedelta(days=1)

    with pytest.raises(HTTPException) as exc_info:
        validate_date_range(today, future)

    assert exc_info.value.status_code == 422
    assert "future" in exc_info.value.detail


def test_today_as_end_date_passes():
    today = date.today()
    validate_date_range(today, today)
