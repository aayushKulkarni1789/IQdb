from datetime import date, time
from enum import Enum
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import Date, Time, and_, cast, func, literal

from app.models import Image
from app.search.filter import FilterKind, SubsetFilter

try:
    _DATETIME_DESCRIPTION = Path(__file__).with_suffix(".md").read_text(encoding="utf-8")
except FileNotFoundError:
    _DATETIME_DESCRIPTION = ""


class DayOfWeek(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


# PostgreSQL EXTRACT(DOW FROM timestamp) mapping: MONDAY=1 ... SATURDAY=6, SUNDAY=0
_DOW_TO_INT: dict[DayOfWeek, int] = {
    DayOfWeek.MONDAY: 1,
    DayOfWeek.TUESDAY: 2,
    DayOfWeek.WEDNESDAY: 3,
    DayOfWeek.THURSDAY: 4,
    DayOfWeek.FRIDAY: 5,
    DayOfWeek.SATURDAY: 6,
    DayOfWeek.SUNDAY: 0,
}


class DatetimeFilterSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal[FilterKind.DATETIME] = FilterKind.DATETIME
    date_lower: date | None = None
    date_upper: date | None = None
    time_lower: time | None = None
    time_upper: time | None = None
    days_included: list[DayOfWeek] | None = None

    @model_validator(mode="after")
    def _validate_ranges(self) -> "DatetimeFilterSpec":
        if self.date_lower is not None and self.date_upper is not None:
            if self.date_lower > self.date_upper:
                raise ValueError(
                    f"date_lower ({self.date_lower}) must be <= date_upper ({self.date_upper})"
                )
        if self.time_lower is not None and self.time_upper is not None:
            if self.time_lower > self.time_upper:
                raise ValueError(
                    f"time_lower ({self.time_lower}) must be <= time_upper ({self.time_upper})"
                )
        return self


class DatetimeFilter(SubsetFilter):
    kind = FilterKind.DATETIME
    is_live = True
    spec_model = DatetimeFilterSpec
    SPEC_FORMAT: ClassVar[str] = (
        '{"kind": "datetime", "date_lower": "2024-01-01", "date_upper": "2024-12-31", '
        '"time_lower": "08:00:00", "time_upper": "18:00:00", '
        '"days_included": ["MONDAY", "WEDNESDAY"]}'
    )
    SPEC_EXAMPLE: ClassVar[dict] = {
        "kind": "datetime",
        "date_lower": "2024-01-01",
        "date_upper": "2024-12-31",
        "time_lower": "08:00:00",
        "time_upper": "18:00:00",
        "days_included": ["MONDAY", "WEDNESDAY"],
    }
    DESCRIPTION: ClassVar[str] = _DATETIME_DESCRIPTION

    def __init__(
        self,
        date_lower: date | None = None,
        date_upper: date | None = None,
        time_lower: time | None = None,
        time_upper: time | None = None,
        days_included: list[DayOfWeek] | None = None,
    ) -> None:
        self.date_lower = date_lower
        self.date_upper = date_upper
        self.time_lower = time_lower
        self.time_upper = time_upper
        self.days_included = days_included

    def build_predicate(self):
        predicates = []
        if self.date_lower is not None:
            predicates.append(cast(Image.capture_time, Date) >= self.date_lower)
        if self.date_upper is not None:
            predicates.append(cast(Image.capture_time, Date) <= self.date_upper)
        if self.time_lower is not None:
            predicates.append(cast(Image.capture_time, Time) >= self.time_lower)
        if self.time_upper is not None:
            predicates.append(cast(Image.capture_time, Time) <= self.time_upper)
        if self.days_included:
            dow_values = [_DOW_TO_INT[d] for d in self.days_included]
            predicates.append(func.extract("dow", Image.capture_time).in_(dow_values))
        if not predicates:
            return literal(True)
        if len(predicates) == 1:
            return predicates[0]
        return and_(*predicates)

    def to_spec(self) -> dict:
        spec: dict = {"kind": str(FilterKind.DATETIME)}
        if self.date_lower is not None:
            spec["date_lower"] = self.date_lower.isoformat()
        if self.date_upper is not None:
            spec["date_upper"] = self.date_upper.isoformat()
        if self.time_lower is not None:
            spec["time_lower"] = self.time_lower.isoformat()
        if self.time_upper is not None:
            spec["time_upper"] = self.time_upper.isoformat()
        if self.days_included is not None:
            spec["days_included"] = [d.value for d in self.days_included]
        return spec

    @classmethod
    def from_spec(cls, spec_model: DatetimeFilterSpec) -> "DatetimeFilter":
        return cls(
            date_lower=spec_model.date_lower,
            date_upper=spec_model.date_upper,
            time_lower=spec_model.time_lower,
            time_upper=spec_model.time_upper,
            days_included=spec_model.days_included,
        )
