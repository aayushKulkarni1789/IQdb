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
        "limit": 10,
    }
    results = _fetch_nominatim(params)
    if not results:
        raise GeocodingError(f"Location not found: {location_text!r}")

    # 1. First priority: look for a hit containing an actual Polygon or MultiPolygon
    for hit in results:
        geojson = hit.get("geojson")
        if geojson and geojson.get("type") in ("Polygon", "MultiPolygon"):
            logger.info(
                "get_location_polygon('%s') -> found %s from hit '%s'",
                location_text,
                hit.get("display_name", ""),
            )
            return geojson

    # 2. Fallback: construct rectangular polygon from boundingbox if available
    for hit in results:
        bbox = hit.get("boundingbox")
        if bbox and len(bbox) == 4:
            try:
                south, north = float(bbox[0]), float(bbox[1])
                west, east = float(bbox[2]), float(bbox[3])
                if south != north and west != east:
                    bbox_polygon = {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [west, south],
                                [east, south],
                                [east, north],
                                [west, north],
                                [west, south],
                            ]
                        ],
                    }
                    logger.info(
                        "get_location_polygon('%s') -> constructed bounding box polygon for '%s': %s",
                        location_text,
                        hit.get("display_name", ""),
                        bbox_polygon,
                    )
                    return bbox_polygon
            except (ValueError, TypeError):
                continue

    # 3. If only a single point or no valid boundingbox exists
    top_geojson = results[0].get("geojson")
    if top_geojson:
        logger.warning(
            "get_location_polygon('%s') -> no polygon/multipolygon or boundingbox found, using raw geojson: %s",
            location_text,
            top_geojson,
        )
        return top_geojson

    raise GeocodingError(f"No polygon geometry or bounding box found for location: {location_text!r}")


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
