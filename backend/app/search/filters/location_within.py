import json
import logging
from pathlib import Path
from typing import ClassVar, Literal

from geoalchemy2 import Geometry
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, cast, func

from app.models import Image
from app.search.filter import FilterKind, SubsetFilter
from app.search.geocoding import get_location_polygon

logger = logging.getLogger(__name__)

try:
    _DESCRIPTION = Path(__file__).with_suffix(".md").read_text(encoding="utf-8")
except FileNotFoundError:
    _DESCRIPTION = ""


class LocationWithinSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Literal[FilterKind.LOCATION_WITHIN] = FilterKind.LOCATION_WITHIN
    location_text: str


class LocationWithinFilter(SubsetFilter):
    kind = FilterKind.LOCATION_WITHIN
    is_live = True
    spec_model = LocationWithinSpec
    SPEC_FORMAT: ClassVar[str] = (
        '{"kind": "location_within", "location_text": "<place name>"}'
    )
    SPEC_EXAMPLE: ClassVar[dict] = {
        "kind": "location_within",
        "location_text": "Paris",
    }
    DESCRIPTION: ClassVar[str] = _DESCRIPTION

    def __init__(self, location_text: str) -> None:
        self.location_text = location_text

    def to_spec(self) -> dict:
        return {
            "kind": str(FilterKind.LOCATION_WITHIN),
            "location_text": self.location_text,
        }

    @classmethod
    def from_spec(cls, spec_model: LocationWithinSpec) -> "LocationWithinFilter":
        return cls(location_text=spec_model.location_text)

    def build_predicate(self):
        geojson_dict = get_location_polygon(self.location_text)
        logger.info(
            "location_within build_predicate for '%s': geojson_type=%s, geojson=%s",
            self.location_text,
            geojson_dict.get("type"),
            geojson_dict,
        )
        polygon_geom = func.ST_SetSRID(
            func.ST_GeomFromGeoJSON(json.dumps(geojson_dict)),
            4326,
        )
        return and_(
            Image.location.isnot(None),
            func.ST_Within(cast(Image.location, Geometry), polygon_geom),
        )
