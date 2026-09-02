from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import seed_images
from app.search.registry import from_spec


def test_v2_query_valid_returns_hits(client: TestClient, db_session: Session, monkeypatch):
    seed_images(db_session, 5)

    # Mock agent to return a clip filter
    def fake_invoke(user_text: str):
        f = from_spec({"kind": "clip", "text": "a cat"})
        return {"filters": [f], "messages": []}

    monkeypatch.setattr("app.search.agent.llm.invoke", fake_invoke)
    # Also mock clip embeddings for ranking
    from app.core import clip as clip_module

    V = [1.0 if i == 0 else 0.0 for i in range(512)]
    monkeypatch.setattr(clip_module, "get_text_embeddings", lambda texts: [list(V) for _ in texts])

    resp = client.post("/api/v2/search/query", json={"user_text": "cats", "top_k": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert "number_of_images_in_output" in body
    assert "hits" in body
    assert len(body["hits"]) == 5
    for hit in body["hits"]:
        assert "id" in hit and "uri" in hit and "score" in hit


def test_v2_query_empty_filters_returns_422(client: TestClient, monkeypatch):
    def fake_invoke(user_text: str):
        return {"filters": [], "messages": []}

    monkeypatch.setattr("app.search.agent.llm.invoke", fake_invoke)

    resp = client.post("/api/v2/search/query", json={"user_text": "empty", "top_k": 10})
    assert resp.status_code == 422


def test_v2_query_top_k_limits(client: TestClient, db_session: Session, monkeypatch):
    seed_images(db_session, 10)

    def fake_invoke(user_text: str):
        f = from_spec({"kind": "datetime"})
        return {"filters": [f], "messages": []}

    monkeypatch.setattr("app.search.agent.llm.invoke", fake_invoke)

    resp = client.post("/api/v2/search/query", json={"user_text": "any", "top_k": 3})
    assert resp.status_code == 200
    assert len(resp.json()["hits"]) == 3


def test_v2_query_no_thumbnail_field(client: TestClient, db_session: Session, monkeypatch):
    seed_images(db_session, 2)

    def fake_invoke(user_text: str):
        f = from_spec({"kind": "clip", "text": "cat"})
        return {"filters": [f], "messages": []}

    from app.core import clip as clip_module

    V = [1.0 if i == 0 else 0.0 for i in range(512)]
    monkeypatch.setattr(clip_module, "get_text_embeddings", lambda texts: [list(V) for _ in texts])
    monkeypatch.setattr("app.search.agent.llm.invoke", fake_invoke)

    resp = client.post("/api/v2/search/query", json={"user_text": "cat", "top_k": 10})
    assert resp.status_code == 200
    for hit in resp.json()["hits"]:
        assert "thumbnail" not in hit
