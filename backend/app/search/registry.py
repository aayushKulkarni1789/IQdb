from typing import Any

from pydantic import ValidationError

from app.search.filter import Filter, FilterKind, InvalidFilterSpecError
from app.search.filters.clip import ClipRank
from app.search.filters.datetime import DatetimeFilter
from app.search.filters.face import FaceFilter
from app.search.filters.geo import GeoFilter


# Registry keyed off the FilterKind enum (design D5); the incoming spec string
# is converted to the enum before lookup so unknown values never silently miss.
REGISTRY: dict[FilterKind, type[Filter]] = {
    FilterKind.CLIP: ClipRank,
    FilterKind.DATETIME: DatetimeFilter,
    FilterKind.GEO: GeoFilter,
    FilterKind.FACE: FaceFilter,
}


class UnknownFilterKindError(ValueError):
    pass


def from_spec(spec: dict[str, Any]) -> Filter:
    """Validate and reconstruct a filter from its spec.

    Raises :class:`UnknownFilterKindError` for unknown ``kind`` values and
    :class:`InvalidFilterSpecError` for specs with a valid kind but malformed
    fields.
    """
    if not isinstance(spec, dict):
        raise UnknownFilterKindError("Filter spec must be an object")
    raw_kind = spec.get("kind")
    try:
        kind = FilterKind(raw_kind)
    except ValueError:
        valid = ", ".join(k.value for k in FilterKind)
        raise UnknownFilterKindError(
            f"Unknown filter kind: {raw_kind!r}. Valid values: {valid}"
        ) from None
    cls = REGISTRY[kind]
    try:
        validated_model = cls.spec_model.model_validate(spec)
    except ValidationError as exc:
        raise InvalidFilterSpecError.from_validation(
            kind=kind,
            exc=exc,
            fmt=cls.SPEC_FORMAT,
            example=cls.SPEC_EXAMPLE,
        ) from exc
    return cls.from_spec(validated_model)


def list_filters() -> list[dict[str, Any]]:
    """Advertise which filters are live vs not-implemented (D6 / spec)."""
    return [{"kind": str(kind), "live": cls.is_live} for kind, cls in REGISTRY.items()]
