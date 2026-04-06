from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.api.constants import MAX_DATE_RANGE_DAYS
from app.platform.constants import TIMEZONE
from app.shared.exceptions import ValidationError

_WARSAW = ZoneInfo(TIMEZONE)


def validate_date_range(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise ValidationError("start_date must be <= end_date")
    if (end_date - start_date).days > MAX_DATE_RANGE_DAYS:
        raise ValidationError(f"Date range cannot exceed {MAX_DATE_RANGE_DAYS} days")
    if end_date > datetime.now(_WARSAW).date():
        raise ValidationError("end_date cannot be in the future")
