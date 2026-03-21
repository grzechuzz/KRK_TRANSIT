from datetime import date

from app.common.constants import MAX_DATE_RANGE_DAYS
from app.common.exceptions import ValidationError


def validate_date_range(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise ValidationError("start_date must be <= end_date")
    if (end_date - start_date).days > MAX_DATE_RANGE_DAYS:
        raise ValidationError(f"Date range cannot exceed {MAX_DATE_RANGE_DAYS} days")
    if end_date > date.today():
        raise ValidationError("end_date cannot be in the future")
