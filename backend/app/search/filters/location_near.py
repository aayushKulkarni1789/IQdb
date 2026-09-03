from pathlib import Path
from typing import ClassVar, Literal

from geoalchemy2 import Geography
from pydantic import BaseModel, ConfigDict
from sqlalchemy import cast, func, literal, select

from app.models import Image
from app.search.filter import FilterKind, RankFilter
from app.search.geocoding import get_location_point

try:
    _DESCRIPTION = Path(__file__).with_suffix(".md").read_text(encoding="utf-8")
except FileNotFoundError:
    _DESCRIPTION = ""


class LocationNearSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal[FilterKind.LOCATION_NEAR] = FilterKind.LOCATION_NEAR
    location_text: str
    weight: float = 1.0


class LocationNearRank(RankFilter):
    kind = FilterKind.LOCATION_NEAR
    is_live = True
    spec_model = LocationNearSpec
    SPEC_FORMAT: ClassVar[str] = (
        '{"kind": "location_near", "location_text": "<place name>", "weight": <float, default 1.0>}'
    )
    SPEC_EXAMPLE: ClassVar[dict] = {
        "kind": "location_near",
        "location_text": "Eiffel Tower",
        "weight": 1.0,
    }
    DESCRIPTION: ClassVar[str] = _DESCRIPTION

    def __init__(self, location_text: str, weight: float = 1.0) -> None:
        self.location_text = location_text
        self.weight = weight

    def to_spec(self) -> dict:
        return {
            "kind": str(FilterKind.LOCATION_NEAR),
            "location_text": self.location_text,
            "weight": self.weight,
        }

    @classmethod
    def from_spec(cls, spec_model: LocationNearSpec) -> "LocationNearRank":
        return cls(location_text=spec_model.location_text, weight=spec_model.weight)

    def build_rank_cte(self, candidates):
        lat, lon = get_location_point(self.location_text)
        target_point = cast(func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326), Geography)
        distance = Image.location.op("<->")(target_point)
        subq = candidates.subquery()
        return (
            select(
                subq.c.id.label("id"),
                func.row_number().over(order_by=distance).label("rank"),
                literal(self.weight).label("weight"),
            )
            .select_from(subq.join(Image, Image.id == subq.c.id))
            .where(Image.location.isnot(None))
        )
