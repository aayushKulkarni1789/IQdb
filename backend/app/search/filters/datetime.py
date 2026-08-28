from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

from app.search.filter import FilterKind, SubsetFilter


class DatetimeFilterSpec(BaseModel):
    # Spec shape reserved for the future datetime implementation; only the
    # kind field is required today (design D6).
    model_config = ConfigDict(extra="ignore")

    kind: Literal[FilterKind.DATETIME] = FilterKind.DATETIME


class DatetimeFilter(SubsetFilter):
    kind = FilterKind.DATETIME
    is_live = False
    spec_model = DatetimeFilterSpec
    SPEC_FORMAT: ClassVar[str] = '{"kind": "datetime"}'
    SPEC_EXAMPLE: ClassVar[dict] = {"kind": "datetime"}

    def build_predicate(self):
        raise NotImplementedError(
            "DatetimeFilter requires EXIF capture-time ingestion (intended SQL: EXIF capture_time BETWEEN <start> AND <end>). Not yet implemented."
        )

    def to_spec(self) -> dict:
        return {"kind": str(FilterKind.DATETIME)}

    @classmethod
    def from_spec(cls, spec_model: DatetimeFilterSpec) -> "DatetimeFilter":
        return cls()
