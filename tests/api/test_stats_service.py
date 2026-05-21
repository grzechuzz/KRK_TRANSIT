from datetime import date
from decimal import Decimal

import msgspec

from app.api.services.stats_service import StatsService


class FakeStatsRepository:
    def __init__(self, rows: list[dict[str, object]], trips: int = 1):
        self._rows = rows
        self._trips = trips
        self.trend_calls = 0
        self.trip_count_calls = 0

    def trips_count(self, line_number: str, start_date: date, end_date: date) -> int:
        self.trip_count_calls += 1
        return self._trips

    def trend(
        self, line_number: str, start_date: date, end_date: date, include_estimated: bool = False
    ) -> list[dict[str, object]]:
        self.trend_calls += 1
        return self._rows


def test_trend_normalizes_decimal_average(monkeypatch):
    repo = FakeStatsRepository(
        [
            {
                "date": date(2026, 4, 18),
                "avg_delay_seconds": Decimal("415.5"),
                "trips_count": 23,
            }
        ]
    )
    service = StatsService(repo)  # type: ignore[arg-type]
    cached_payloads: list[object] = []

    monkeypatch.setattr("app.api.services.stats_service.cache.get_cached", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "app.api.services.stats_service.cache.set_cached",
        lambda *args, **kwargs: cached_payloads.append(args[4]),
    )

    result = service.trend("503", date(2026, 3, 11), date(2026, 4, 18))

    assert result.days[0].date == "2026-04-18"
    assert result.days[0].avg_delay_seconds == 415.5
    assert isinstance(result.days[0].avg_delay_seconds, float)
    assert cached_payloads


def test_trend_rebuilds_when_cached_payload_has_string_average(monkeypatch):
    repo = FakeStatsRepository(
        [
            {
                "date": date(2026, 4, 18),
                "avg_delay_seconds": Decimal("415.5"),
                "trips_count": 23,
            }
        ]
    )
    service = StatsService(repo)  # type: ignore[arg-type]
    bad_cached = msgspec.json.encode(
        {
            "line_number": "503",
            "start_date": "2026-03-11",
            "end_date": "2026-04-18",
            "days": [{"date": "2026-04-18", "avg_delay_seconds": "415.5", "trips_count": 23}],
        }
    )
    cached_payloads: list[object] = []

    monkeypatch.setattr("app.api.services.stats_service.cache.get_cached", lambda *args, **kwargs: bad_cached)
    monkeypatch.setattr(
        "app.api.services.stats_service.cache.set_cached",
        lambda *args, **kwargs: cached_payloads.append(args[4]),
    )

    result = service.trend("503", date(2026, 3, 11), date(2026, 4, 18))

    assert result.days[0].avg_delay_seconds == 415.5
    assert repo.trip_count_calls == 1
    assert repo.trend_calls == 1
    assert cached_payloads
