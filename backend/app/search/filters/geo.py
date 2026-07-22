from app.search.filter import SubsetFilter


class GeoFilter(SubsetFilter):
    kind = "geo"
    is_live = False

    def build_predicate(self):
        raise NotImplementedError(
            "GeoFilter requires geo columns / PostGIS (intended SQL: ST_DWithin(...) or haversine distance). Not yet implemented."
        )

    def to_spec(self) -> dict:
        return {"kind": "geo"}

    @classmethod
    def from_spec(cls, spec: dict) -> "GeoFilter":
        return cls()
