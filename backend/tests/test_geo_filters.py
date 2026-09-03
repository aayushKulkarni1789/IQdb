import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.crud import create_image
from app.models import Image
from app.search.agent.tools import add_location_near_filter, add_location_within_filter
from app.search.filter import CandidateQuery, FilterKind
from app.search.filters.location_near import LocationNearRank, LocationNearSpec
from app.search.filters.location_within import LocationWithinFilter, LocationWithinSpec
from app.search.geocoding import (
    GeocodingError,
    get_location_point,
    get_location_polygon,
)
from app.search.registry import from_spec, list_filters

PARIS_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [2.22, 48.81],
            [2.47, 48.81],
            [2.47, 48.91],
            [2.22, 48.91],
            [2.22, 48.81],
        ]
    ],
}

MOCK_GEOCODING_DATA = {
    "Paris": [
        {
            "lat": "48.8566",
            "lon": "2.3522",
            "display_name": "Paris, France",
            "geojson": PARIS_POLYGON,
        }
    ],
    "Eiffel Tower": [
        {
            "lat": "48.8584",
            "lon": "2.2945",
            "display_name": "Eiffel Tower, Paris, France",
            "geojson": {
                "type": "Point",
                "coordinates": [2.2945, 48.8584],
            },
        }
    ],
    "London": [
        {
            "lat": "51.5074",
            "lon": "-0.1278",
            "display_name": "London, UK",
            "geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-0.51, 51.28],
                        [0.33, 51.28],
                        [0.33, 51.69],
                        [-0.51, 51.69],
                        [-0.51, 51.28],
                    ]
                ],
            },
        }
    ],
}


def mock_fetch_nominatim(params):
    q = params.get("q", "")
    if q in MOCK_GEOCODING_DATA:
        return MOCK_GEOCODING_DATA[q]
    return []


@pytest.fixture(autouse=True)
def mock_nominatim():
    """Ensure no tests ever make real HTTP calls to Nominatim."""
    with patch("app.search.geocoding._fetch_nominatim", side_effect=mock_fetch_nominatim):
        # Clear lru cache before each test
        get_location_polygon.cache_clear()
        get_location_point.cache_clear()
        yield


def test_geocoding_service_mocked():
    point = get_location_point("Paris")
    assert point == (48.8566, 2.3522)

    polygon = get_location_polygon("Paris")
    assert polygon["type"] == "Polygon"

    with pytest.raises(GeocodingError):
        get_location_point("NonExistentLocation12345")

    with pytest.raises(GeocodingError):
        get_location_point("")


def test_registry_contains_location_filters():
    filters = list_filters()
    kinds = {f["kind"]: f["live"] for f in filters}
    assert kinds.get("location_within") is True
    assert kinds.get("location_near") is True


def test_from_spec_location_filters():
    spec_within = {"kind": "location_within", "location_text": "Paris"}
    f_within = from_spec(spec_within)
    assert isinstance(f_within, LocationWithinFilter)
    assert f_within.to_spec() == spec_within

    spec_near = {"kind": "location_near", "location_text": "Eiffel Tower", "weight": 1.5}
    f_near = from_spec(spec_near)
    assert isinstance(f_near, LocationNearRank)
    assert f_near.weight == 1.5
    assert f_near.to_spec() == spec_near


def test_agent_tools_add_location_filters():
    runtime = MagicMock()
    runtime.state = {"filters": []}
    runtime.tool_call_id = "call_123"

    cmd1 = add_location_within_filter.func(location_text="Paris", runtime=runtime)
    assert not isinstance(cmd1, str)
    assert len(cmd1.update["filters"]) == 1
    assert isinstance(cmd1.update["filters"][0], LocationWithinFilter)

    runtime.state = {"filters": cmd1.update["filters"]}
    cmd2 = add_location_near_filter.func(location_text="Eiffel Tower", weight=1.2, runtime=runtime)
    assert not isinstance(cmd2, str)
    assert len(cmd2.update["filters"]) == 2
    assert isinstance(cmd2.update["filters"][1], LocationNearRank)


def test_location_within_and_near_queries(db_session: Session):
    # Seed 3 images:
    # Image 1: In Paris (lat 48.8566, lon 2.3522) - very close to Eiffel Tower
    # Image 2: In London (lat 51.5074, lon -0.1278) - far from Eiffel Tower
    # Image 3: No GPS (lat=None, lon=None)
    img_paris = create_image(
        db_session,
        filename="paris.jpg",
        uri="test/paris.jpg",
        latitude=48.8566,
        longitude=2.3522,
    )
    img_london = create_image(
        db_session,
        filename="london.jpg",
        uri="test/london.jpg",
        latitude=51.5074,
        longitude=-0.1278,
    )
    img_nogps = create_image(
        db_session,
        filename="nogps.jpg",
        uri="test/nogps.jpg",
        latitude=None,
        longitude=None,
    )
    db_session.commit()

    # 1. Test location_within("Paris") subset filter
    within_filter = LocationWithinFilter(location_text="Paris")
    cq = CandidateQuery(subset_filters=[within_filter], rank_filters=[])
    assert cq.candidate_count(db_session) == 1
    hits = cq.finalize(db_session, top_k=10)
    assert len(hits) == 1
    assert hits[0][0] == img_paris.id

    # 2. Test location_near("Eiffel Tower") rank filter
    near_filter = LocationNearRank(location_text="Eiffel Tower")
    cq_near = CandidateQuery(subset_filters=[], rank_filters=[near_filter])
    hits_near = cq_near.finalize(db_session, top_k=10)
    # Both paris and london have GPS, paris is closer to Eiffel Tower
    assert len(hits_near) == 2
    assert hits_near[0][0] == img_paris.id
    assert hits_near[1][0] == img_london.id


def test_sessions_api_with_geo_filters(client: TestClient, db_session: Session):
    img_paris = create_image(
        db_session,
        filename="paris_api.jpg",
        uri="test/paris_api.jpg",
        latitude=48.8566,
        longitude=2.3522,
    )
    img_london = create_image(
        db_session,
        filename="london_api.jpg",
        uri="test/london_api.jpg",
        latitude=51.5074,
        longitude=-0.1278,
    )
    db_session.commit()

    # Create session
    resp = client.post("/api/v1/sessions")
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    # Add location_within filter
    resp = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "location_within", "location_text": "Paris"},
    )
    assert resp.status_code == 200
    assert resp.json()["candidate_count"] == 1

    # Add location_near filter
    resp = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "location_near", "location_text": "Eiffel Tower", "weight": 1.0},
    )
    assert resp.status_code == 200

    # Finalize session
    resp = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        json={"top_k": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["number_of_images_in_output"] == 1
    assert data["hits"][0]["id"] == img_paris.id
