from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.shared.gtfs.timeparse import (
    compute_delay_seconds,
    compute_planned_time,
    compute_service_date,
    parse_gtfs_time_to_seconds,
)


class TestParseGtfsTimeToSeconds:
    @pytest.mark.parametrize(
        "time_input, expected_seconds",
        [
            ("00:00:00", 0),
            ("08:30:00", 30600),
            ("12:00:00", 43200),
            ("23:59:59", 86399),
            ("24:00:00", 86400),
            ("25:30:00", 91800),
            ("26:00:00", 93600),
            ("  08:30:00  ", 30600),
        ],
    )
    def test_valid_parsing(self, time_input, expected_seconds):
        assert parse_gtfs_time_to_seconds(time_input) == expected_seconds

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "08:30",
            "08:30:00:00",
            "08:60:00",
            "08:30:60",
            "ab:cd:ef",
            None,
        ],
    )
    def test_invalid_parsing_raises_error(self, invalid_input):
        with pytest.raises(ValueError):
            parse_gtfs_time_to_seconds(invalid_input)


class TestComputeServiceDate:
    @pytest.mark.parametrize(
        "event_dt, scheduled_sec, expected_date",
        [
            (datetime(2025, 1, 10, 14, 30, tzinfo=UTC), 52200, date(2025, 1, 10)),
            (datetime(2025, 1, 10, 1, 30, tzinfo=UTC), 91800, date(2025, 1, 9)),
            (datetime(2025, 1, 10, 0, 0, tzinfo=UTC), 86400, date(2025, 1, 9)),
            (datetime(2025, 1, 10, 22, 59, 59, tzinfo=UTC), 86399, date(2025, 1, 10)),
        ],
    )
    def test_calculate_service_date(self, event_dt, scheduled_sec, expected_date):
        assert compute_service_date(event_dt, scheduled_sec) == expected_date


class TestComputePlannedTime:
    @pytest.mark.parametrize(
        "service_date, scheduled_sec, expected_tuple",
        [
            (date(2025, 1, 10), 52200, (2025, 1, 10, 14, 30)),
            (date(2025, 1, 9), 91800, (2025, 1, 10, 1, 30)),
            (date(2025, 1, 10), 0, (2025, 1, 10, 0, 0)),
        ],
    )
    def test_calculate_planned_time(self, service_date, scheduled_sec, expected_tuple):
        tz = ZoneInfo("Europe/Warsaw")
        result = compute_planned_time(service_date, scheduled_sec, tz)

        assert result.year == expected_tuple[0]
        assert result.month == expected_tuple[1]
        assert result.day == expected_tuple[2]
        assert result.hour == expected_tuple[3]
        assert result.minute == expected_tuple[4]
        assert result.tzinfo == tz


class TestComputeDelaySeconds:
    @pytest.mark.parametrize(
        "event_dt, planned_dt, expected_delay",
        [
            (datetime(2025, 1, 10, 14, 30), datetime(2025, 1, 10, 14, 30), 0),
            (datetime(2025, 1, 10, 14, 35), datetime(2025, 1, 10, 14, 30), 300),
            (datetime(2025, 1, 10, 14, 28), datetime(2025, 1, 10, 14, 30), -120),
            (datetime(2025, 1, 10, 15, 30), datetime(2025, 1, 10, 14, 30), 3600),
        ],
    )
    def test_calculate_delay(self, event_dt, planned_dt, expected_delay):
        assert compute_delay_seconds(event_dt, planned_dt) == expected_delay
