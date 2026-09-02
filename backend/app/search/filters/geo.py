from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

from app.search.filter import FilterKind, SubsetFilter

try:
    _GEO_DESCRIPTION = Path(__file__).with_suffix(".md").read_text(encoding="utf-8")
except FileNotFoundError:
    _GEO_DESCRIPTION = ""


class GeoFilterSpec(BaseModel):
    # Spec shape reserved for the future geo implementation; only the kind
    # field is required today (design D6).
    model_config = ConfigDict(extra="ignore")

    kind: Literal[FilterKind.GEO] = FilterKind.GEO


class GeoFilter(SubsetFilter):
    kind = FilterKind.GEO
    is_live = False
    spec_model = GeoFilterSpec
    SPEC_FORMAT: ClassVar[str] = '{"kind": "geo"}'
    SPEC_EXAMPLE: ClassVar[dict] = {"kind": "geo"}
    DESCRIPTION: ClassVar[str] = _GEO_DESCRIPTION

    def build_predicate(self):
        raise NotImplementedError(
            "GeoFilter requires geo columns / PostGIS (intended SQL: ST_DWithin(...) or haversine distance). Not yet implemented."
        )

    def to_spec(self) -> dict:
        return {"kind": str(FilterKind.GEO)}

    @classmethod
    def from_spec(cls, spec_model: GeoFilterSpec) -> "GeoFilter":
        return cls()
