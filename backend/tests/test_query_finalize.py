from sqlmodel import Session

from app.search.query import finalize
from app.search.registry import from_spec
from tests.conftest import seed_images


def test_finalize_subset_only_returns_score_null(db_session: Session):
    seed_images(db_session, 5)
    # Empty datetime spec matches all (literal True) – avoids capture_time NULL issue
    f = from_spec({"kind": "datetime"})
    count, hits = finalize(db_session, [f], top_k=100)
    assert count == 5
    assert all(score is None for _, _, score in hits)
    ids = [h[0] for h in hits]
    assert ids == sorted(ids)


def test_finalize_rank_only_returns_scores(db_session: Session, monkeypatch):
    from app.core import clip as clip_module

    V = [1.0 if i == 0 else 0.0 for i in range(512)]
    monkeypatch.setattr(clip_module, "get_text_embeddings", lambda texts: [list(V) for _ in texts])

    seed_images(db_session, 6)
    f = from_spec({"kind": "clip", "text": "query"})
    count, hits = finalize(db_session, [f], top_k=100)
    assert count == 6
    assert all(score is not None for _, _, score in hits)


def test_finalize_mixed_subset_and_rank(db_session: Session, monkeypatch):
    from app.core import clip as clip_module

    V = [1.0 if i == 0 else 0.0 for i in range(512)]
    monkeypatch.setattr(clip_module, "get_text_embeddings", lambda texts: [list(V) for _ in texts])

    seed_images(db_session, 5)
    # datetime filter that matches all (empty spec), clip rank
    f_dt = from_spec({"kind": "datetime"})
    f_clip = from_spec({"kind": "clip", "text": "anything"})
    count, hits = finalize(db_session, [f_dt, f_clip], top_k=10)
    assert count == 5
    assert all(h[2] is not None for h in hits)


def test_finalize_same_kind_subset_or(db_session: Session):
    # Two datetime filters with same kind should be ORed
    from app.models import Image

    seed_images(db_session, 5)
    # Create filters that match different ids via raw subset filter test
    # Use datetime filters with disjoint date ranges but we control capture_time via seed_images (no capture_time)
    # So instead test OR via CandidateQuery directly using dummy filters that mimic same-kind
    from app.search.filter import CandidateQuery, SubsetFilter

    class _KindA1(SubsetFilter):
        kind = "_test_kind_a"

        def build_predicate(self):
            return Image.id == 1

    class _KindA2(SubsetFilter):
        kind = "_test_kind_a"

        def build_predicate(self):
            return Image.id == 2

    cq_count, cq_hits = finalize(db_session, [_KindA1(), _KindA2()], top_k=100)
    assert cq_count == 2
    assert sorted(h[0] for h in cq_hits) == [1, 2]


def test_finalize_top_k_limits(db_session: Session):
    seed_images(db_session, 10)
    f = from_spec({"kind": "datetime"})
    count, hits = finalize(db_session, [f], top_k=3)
    assert len(hits) == 3
    assert count == 3


def test_finalize_empty_filters_returns_all_ordered_by_id(db_session: Session):
    # Empty filter list -> CandidateQuery with no filters -> returns all ordered by id
    seed_images(db_session, 4)
    count, hits = finalize(db_session, [], top_k=100)
    assert count == 4
    assert [h[0] for h in hits] == sorted(h[0] for h in hits)
