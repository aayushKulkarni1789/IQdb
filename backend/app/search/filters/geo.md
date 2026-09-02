# Geo Filter (kind: `geo`) — Subset Filter (stub, not live)

## What it does
Reserved geolocation filter that will narrow candidates by GPS coordinates extracted from EXIF. Intended implementation uses PostGIS `ST_DWithin` or haversine distance against `Image.latitude`/`longitude`. Currently `is_live = False` and `build_predicate` raises `NotImplementedError`.

## How to use
Not available via tools. Spec shape is reserved; adding it now returns a 501 from the tool layer. No live tool is exposed for `geo`.

**Spec format:** `{"kind": "geo"}`

**Example:** `{"kind": "geo"}`

## When to use
Do not use. Planned for future "near this location" queries (e.g., "photos taken in Paris"). Until live, rely on `clip` / `datetime` filters.
