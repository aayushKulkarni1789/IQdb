# Location Near Filter (kind: `location_near`) — Rank Filter

## What it does
Ranks candidate images by their geographic proximity (KNN distance on the spheroid) to a given target location resolved via Nominatim geocoding.

## How to use
Pass `location_text` and an optional `weight` (defaults to 1.0).

**Spec format:** `{"kind": "location_near", "location_text": "<place name>", "weight": <float, default 1.0>}`

**Example:** `{"kind": "location_near", "location_text": "Eiffel Tower", "weight": 1.0}`

## When to use
Use when ranking images by how close they were taken to a landmark, point of interest, address, or coordinate (e.g. "photos taken near Times Square").
