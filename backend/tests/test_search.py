import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import clip as clip_module
from tests.conftest import seed_images


def _create_session(client: TestClient) -> int:
    resp = client.post("/api/v1/sessions")
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_session(client: TestClient) -> None:
    resp = client.post("/api/v1/sessions")
    assert resp.status_code == 201
    body = resp.json()
    assert isinstance(body["id"], int)


def test_apply_filters_in_any_order(client: TestClient) -> None:
    session_id = _create_session(client)
    resp1 = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "clip", "text": "a cat"},
    )
    assert resp1.status_code == 200
    assert isinstance(resp1.json()["candidate_count"], int)

    resp2 = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "clip", "text": "a dog"},
    )
    assert resp2.status_code == 200
    assert isinstance(resp2.json()["candidate_count"], int)


def test_finalize_returns_top_k(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_images(db_session, 10)
    session_id = _create_session(client)
    client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "clip", "text": "anything"},
    )
    resp = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        json={"top_k": 10},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["number_of_images_in_output"], int)
    assert isinstance(body["hits"], list)
    for hit in body["hits"]:
        assert isinstance(hit["id"], int)
        assert hit["score"] is None or isinstance(hit["score"], float)

    re_finalize = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        json={"top_k": 10},
    )
    assert re_finalize.status_code == 409


def test_finalized_session_rejects_ops(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_images(db_session, 3)
    session_id = _create_session(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        json={"top_k": 10},
    )
    assert resp.status_code == 200

    add = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "clip", "text": "x"},
    )
    assert add.status_code == 409

    finalize_again = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        json={"top_k": 10},
    )
    assert finalize_again.status_code == 409


def test_candidate_count_excludes_rank_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    ids = seed_images(db_session, 7)
    session_id = _create_session(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "clip", "text": "only rank"},
    )
    assert resp.status_code == 200
    assert resp.json()["candidate_count"] == len(ids)


def test_rrf_skipped_when_no_rank_filters(
    client: TestClient,
    db_session: Session,
) -> None:
    ids = seed_images(db_session, 5)
    session_id = _create_session(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        json={"top_k": 100},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["number_of_images_in_output"] == len(ids)
    hits = body["hits"]
    assert [h["score"] for h in hits] == [None] * len(hits)
    returned_ids = [h["id"] for h in hits]
    assert returned_ids == sorted(returned_ids)


def test_clip_rank_end_to_end(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    V = [1.0 if i == 0 else 0.0 for i in range(512)]
    monkeypatch.setattr(clip_module, "get_text_embeddings", lambda texts: [list(V) for _ in texts])

    seed_images(db_session, 6)
    session_id = _create_session(client)
    client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "clip", "text": "query"},
    )
    resp = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        json={"top_k": 100},
    )
    assert resp.status_code == 200
    hits = resp.json()["hits"]
    assert len(hits) == 6
    assert all(h["score"] is not None for h in hits)
    assert hits[0]["id"] == 1


def test_stub_filter_rejected_at_add_time(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "datetime"},
    )
    assert resp.status_code == 501

    finalize_resp = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        json={"top_k": 10},
    )
    assert finalize_resp.status_code == 200


def test_registry_advertises_liveness(client: TestClient) -> None:
    resp = client.get("/api/v1/filters")
    assert resp.status_code == 200
    filters = resp.json()
    assert {"kind": "clip", "live": True} in filters
    assert {"kind": "datetime", "live": False} in filters
    assert {"kind": "geo", "live": False} in filters
    assert {"kind": "face", "live": False} in filters
