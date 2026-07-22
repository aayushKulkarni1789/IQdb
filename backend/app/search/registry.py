from typing import Any

from app.search.filter import Filter
from app.search.filters.clip import ClipRank
from app.search.filters.datetime import DatetimeFilter
from app.search.filters.face import FaceFilter
from app.search.filters.geo import GeoFilter


REGISTRY: dict[str, type[Filter]] = {
    "clip": ClipRank,
    "datetime": DatetimeFilter,
    "geo": GeoFilter,
    "face": FaceFilter,
}


class UnknownFilterKindError(ValueError):
    pass


def from_spec(spec: dict[str, Any]) -> Filter:
    """Validate and reconstruct a filter from its spec.

    Raises :class:`UnknownFilterKindError` for unknown ``kind`` values.
    """
    if not isinstance(spec, dict):
        raise UnknownFilterKindError("Filter spec must be an object")
    kind = spec.get("kind")
    if kind not in REGISTRY:
        raise UnknownFilterKindError(f"Unknown filter kind: {kind!r}")
    return REGISTRY[kind].from_spec(spec)


def list_filters() -> list[dict[str, Any]]:
    """Advertise which filters are live vs not-implemented (D6 / spec)."""
    return [{"kind": kind, "live": cls.is_live} for kind, cls in REGISTRY.items()]
