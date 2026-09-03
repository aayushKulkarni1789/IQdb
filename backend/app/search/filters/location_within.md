# Location Within Filter (kind: `location_within`) — Subset Filter

## What it does
Filters images to only those whose GPS location is geographically within the polygon boundary of a specified place, city, region, or boundary resolved via Nominatim geocoding.

## How to use
Pass `location_text` naming the desired location.

**Spec format:** `{"kind": "location_within", "location_text": "<place name>"}`

**Example:** `{"kind": "location_within", "location_text": "Paris"}`

## When to use
Use when the user wants images taken inside a specific city, country, park, or region (e.g., "photos taken in Paris", "pictures in Central Park").
