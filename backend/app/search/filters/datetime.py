from app.search.filter import SubsetFilter


class DatetimeFilter(SubsetFilter):
    kind = "datetime"
    is_live = False

    def build_predicate(self):
        raise NotImplementedError(
            "DatetimeFilter requires EXIF capture-time ingestion (intended SQL: EXIF capture_time BETWEEN <start> AND <end>). Not yet implemented."
        )

    def to_spec(self) -> dict:
        return {"kind": "datetime"}

    @classmethod
    def from_spec(cls, spec: dict) -> "DatetimeFilter":
        return cls()
