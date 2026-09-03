from functools import lru_cache
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "image search engine agent (imgdb/1.0)"


class GeocodingError(ValueError):
    """Raised when geocoding a location fails or returns no results."""
    pass


def _fetch_nominatim(params: dict[str, Any]) -> list[dict[str, Any]]:
    headers = {"User-Agent": USER_AGENT}
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(NOMINATIM_SEARCH_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                raise GeocodingError(f"Unexpected Nominatim response: {data}")
            return data
    except httpx.HTTPError as exc:
        logger.error("Nominatim request failed: %s", exc)
        raise GeocodingError(f"Nominatim geocoding request failed: {exc}") from exc


@lru_cache(maxsize=256)
def get_location_polygon(location_text: str) -> dict[str, Any]:
    """Geocode a location query string and return its GeoJSON polygon geometry.

    Args:
        location_text: Name of location or place (e.g. 'Paris', 'Central Park').

    Returns:
        GeoJSON geometry dict (e.g. {'type': 'Polygon' | 'MultiPolygon', 'coordinates': ...}).

    Raises:
        GeocodingError: If the location cannot be resolved or has no geometry.
    """
    clean_text = location_text.strip()
    if not clean_text:
        raise GeocodingError("Location text cannot be empty.")

    params = {
        "q": clean_text,
        "format": "json",
        "polygon_geojson": 1,
        "limit": 1,
    }
    results = _fetch_nominatim(params)
    if not results:
        raise GeocodingError(f"Location not found: {location_text!r}")

    top_hit = results[0]
    geojson = top_hit.get("geojson")
    if not geojson:
        raise GeocodingError(f"No polygon geometry found for location: {location_text!r}")

    logger.info("get_location_polygon('%s') -> %s", location_text, geojson)
    return geojson


@lru_cache(maxsize=256)
def get_location_point(location_text: str) -> tuple[float, float]:
    """Geocode a location query string and return its (latitude, longitude) coordinates.

    Args:
        location_text: Name of location or place (e.g. 'Eiffel Tower', 'Tokyo').

    Returns:
        tuple of (latitude: float, longitude: float).

    Raises:
        GeocodingError: If the location cannot be resolved.
    """
    clean_text = location_text.strip()
    if not clean_text:
        raise GeocodingError("Location text cannot be empty.")

    params = {
        "q": clean_text,
        "format": "json",
        "limit": 1,
    }
    results = _fetch_nominatim(params)
    if not results:
        raise GeocodingError(f"Location not found: {location_text!r}")

    top_hit = results[0]
    try:
        lat = float(top_hit["lat"])
        lon = float(top_hit["lon"])
        logger.info("get_location_point('%s') -> lat=%s, lon=%s", location_text, lat, lon)
        return lat, lon
    except (KeyError, ValueError) as exc:
        raise GeocodingError(f"Invalid coordinate format returned for: {location_text!r}") from exc
