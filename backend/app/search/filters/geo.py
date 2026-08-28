from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict

from app.search.filter import FilterKind, SubsetFilter


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

    def build_predicate(self):
        raise NotImplementedError(
            "GeoFilter requires geo columns / PostGIS (intended SQL: ST_DWithin(...) or haversine distance). Not yet implemented."
        )

    def to_spec(self) -> dict:
        return {"kind": str(FilterKind.GEO)}

    @classmethod
    def from_spec(cls, spec_model: GeoFilterSpec) -> "GeoFilter":
        return cls()
