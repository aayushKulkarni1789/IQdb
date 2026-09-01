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
        # Finalize hits carry uri alongside id and score (breaking change).
        assert isinstance(hit["uri"], str) and hit["uri"]
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
    # datetime is now a live filter, should be accepted
    resp = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "datetime"},
    )
    assert resp.status_code == 200

    # geo and face remain stubs and should be rejected with 501
    resp_geo = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "geo"},
    )
    assert resp_geo.status_code == 501

    resp_face = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "face"},
    )
    assert resp_face.status_code == 501

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
    assert {"kind": "datetime", "live": True} in filters
    assert {"kind": "geo", "live": False} in filters
    assert {"kind": "face", "live": False} in filters


def test_unknown_filter_kind_returns_422(
    client: TestClient,
    db_session: Session,
) -> None:
    ids = seed_images(db_session, 3)
    session_id = _create_session(client)

    resp = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "nonexistent_xyz"},
    )
    assert resp.status_code == 422

    # Session still works — the bad spec was not stored
    finalize = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        json={"top_k": 100},
    )
    assert finalize.status_code == 200
    assert finalize.json()["number_of_images_in_output"] == len(ids)


def test_two_phase_execution_with_mixed_filters(db_session: Session) -> None:
    from sqlalchemy import func, literal, select

    from app.models import Image
    from app.search.filter import CandidateQuery, RankFilter, SubsetFilter

    class _AlwaysTrueSubset(SubsetFilter):
        kind = "_test_always_true"

        def build_predicate(self):
            return Image.id > 0

    class _IdRank(RankFilter):
        kind = "_test_id_rank"

        def build_rank_cte(self, candidates):
            subq = candidates.subquery()
            return select(
                subq.c.id.label("id"),
                func.row_number().over(order_by=subq.c.id).label("rank"),
                literal(self.weight).label("weight"),
            ).select_from(subq)

    ids = seed_images(db_session, 5)

    # Construction order 1: subset first, rank second
    cq1 = CandidateQuery(
        subset_filters=[_AlwaysTrueSubset()],
        rank_filters=[_IdRank()],
    )
    results1 = cq1.finalize(db_session, top_k=100)
    assert len(results1) == len(ids)
    assert all(score is not None for _, _, score in results1)
    assert [r[0] for r in results1] == sorted(ids)

    # Construction order 2: rank first, subset second — identical results
    cq2 = CandidateQuery(
        rank_filters=[_IdRank()],
        subset_filters=[_AlwaysTrueSubset()],
    )
    results2 = cq2.finalize(db_session, top_k=100)
    assert results1 == results2


def test_unknown_kind_422_lists_valid_values(client: TestClient) -> None:
    # Strict FilterKind typing rejects unknown kinds at request validation,
    # with pydantic's enum error naming every valid value.
    session_id = _create_session(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "clipp"},
    )
    assert resp.status_code == 422
    detail = str(resp.json())
    for valid in ("clip", "datetime", "geo", "face"):
        assert valid in detail

    # No spec was appended — session still finalizes normally.
    finalize = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        json={"top_k": 10},
    )
    assert finalize.status_code == 200


def test_persisted_string_specs_round_trip(db_session: Session) -> None:
    from app.search.registry import from_spec

    f = from_spec({"kind": "clip", "text": "persisted spec", "weight": 2.0})
    assert isinstance(f, object)
    assert f.to_spec() == {"kind": "clip", "text": "persisted spec", "weight": 2.0}


def test_malformed_clip_spec_returns_structured_422(client: TestClient) -> None:
    # Valid kind but missing required text query: actionable 422 instead of a
    # raw KeyError/500.
    session_id = _create_session(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "clip"},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "Problems:" in detail
    assert "text" in detail
    assert "Expected format:" in detail
    assert "Example:" in detail

    # The bad spec was not appended to the session.
    finalize = client.post(
        f"/api/v1/sessions/{session_id}/finalize",
        json={"top_k": 10},
    )
    assert finalize.status_code == 200


def test_same_kind_subset_filters_compose_with_or(db_session: Session) -> None:
    from sqlalchemy import select

    from app.models import Image
    from app.search.filter import CandidateQuery, SubsetFilter

    class _KindASubset(SubsetFilter):
        kind = "_test_kind_a"

        def build_predicate(self):
            return Image.id == 1

    class _KindASubset2(SubsetFilter):
        kind = "_test_kind_a"

        def build_predicate(self):
            return Image.id == 2

    ids = seed_images(db_session, 5)

    cq = CandidateQuery(
        subset_filters=[_KindASubset(), _KindASubset2()],
        rank_filters=[],
    )
    count = cq.candidate_count(db_session)
    assert count == 2

    results = cq.finalize(db_session, top_k=100)
    returned_ids = [r[0] for r in results]
    assert sorted(returned_ids) == [1, 2]


def test_cross_kind_subset_filters_compose_with_and(db_session: Session) -> None:
    from sqlalchemy import select

    from app.models import Image
    from app.search.filter import CandidateQuery, SubsetFilter

    class _KindXSubset(SubsetFilter):
        kind = "_test_kind_x"

        def build_predicate(self):
            # matches ids 1, 2, 3
            return Image.id <= 3

    class _KindYSubset(SubsetFilter):
        kind = "_test_kind_y"

        def build_predicate(self):
            # matches ids 2, 3, 4
            return Image.id >= 2

    ids = seed_images(db_session, 5)

    cq = CandidateQuery(
        subset_filters=[_KindXSubset(), _KindYSubset()],
        rank_filters=[],
    )
    count = cq.candidate_count(db_session)
    assert count == 2  # intersection: {2, 3}

    results = cq.finalize(db_session, top_k=100)
    returned_ids = [r[0] for r in results]
    assert sorted(returned_ids) == [2, 3]


def test_single_subset_filter_no_regression(db_session: Session) -> None:
    from app.models import Image
    from app.search.filter import CandidateQuery, SubsetFilter

    class _KindZSubset(SubsetFilter):
        kind = "_test_kind_z"

        def build_predicate(self):
            return Image.id <= 2

    ids = seed_images(db_session, 5)

    cq = CandidateQuery(
        subset_filters=[_KindZSubset()],
        rank_filters=[],
    )
    count = cq.candidate_count(db_session)
    assert count == 2

    results = cq.finalize(db_session, top_k=100)
    returned_ids = [r[0] for r in results]
    assert sorted(returned_ids) == [1, 2]


def test_union_same_kind_with_cross_kind_and(db_session: Session) -> None:
    from sqlalchemy import select

    from app.models import Image
    from app.search.filter import CandidateQuery, SubsetFilter

    class _KindM1(SubsetFilter):
        kind = "_test_kind_m"

        def build_predicate(self):
            return Image.id == 1

    class _KindM2(SubsetFilter):
        kind = "_test_kind_m"

        def build_predicate(self):
            return Image.id == 2

    class _KindN(SubsetFilter):
        kind = "_test_kind_n"

        def build_predicate(self):
            # matches 1, 2, 3
            return Image.id <= 3

    ids = seed_images(db_session, 5)

    cq = CandidateQuery(
        subset_filters=[_KindM1(), _KindM2(), _KindN()],
        rank_filters=[],
    )
    count = cq.candidate_count(db_session)
    # M-group: {1} OR {2} = {1,2}; N-group: {1,2,3}; AND = {1,2}
    assert count == 2

    results = cq.finalize(db_session, top_k=100)
    returned_ids = [r[0] for r in results]
    assert sorted(returned_ids) == [1, 2]


def test_unknown_extra_fields_in_spec_are_ignored(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/api/v1/sessions/{session_id}/filters",
        json={"kind": "clip", "text": "a cat", "totally_unknown_field": 123},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["candidate_count"], int)
