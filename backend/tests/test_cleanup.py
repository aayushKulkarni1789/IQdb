import logging

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.cleanup import run_cleanup_pass, safe_run_cleanup_pass
from app.crud import create_search_session, finalize_search_session
from app.models import SearchSession, UploadJob, UploadJobStatus


def _create_job(db: Session, status: UploadJobStatus) -> UploadJob:
    job = UploadJob(job_id=f"job-{status.value}", expected_image_count=1, status=status)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_sweep_deletes_finalized_sessions_only(db_session: Session) -> None:
    finalized = create_search_session(db_session)
    finalize_search_session(db_session, finalized)
    open_session = create_search_session(db_session)

    counts = run_cleanup_pass(db_session)

    assert counts["search_sessions"] >= 1
    remaining = db_session.exec(select(SearchSession)).all()
    assert [s.id for s in remaining] == [open_session.id]


def test_sweep_deletes_terminal_jobs_only(db_session: Session) -> None:
    completed = _create_job(db_session, UploadJobStatus.COMPLETED)
    discarded = _create_job(db_session, UploadJobStatus.DISCARD)
    active_ids = [
        _create_job(db_session, UploadJobStatus.OPEN).id,
        _create_job(db_session, UploadJobStatus.UPLOADING).id,
        _create_job(db_session, UploadJobStatus.UPLOADED).id,
        _create_job(db_session, UploadJobStatus.PROCESSING).id,
    ]
    swept_job_ids = {completed.job_id, discarded.job_id}

    counts = run_cleanup_pass(db_session)

    assert counts["upload_jobs"] >= 2
    remaining = db_session.exec(select(UploadJob)).all()
    remaining_ids = {j.id for j in remaining}
    # Terminal job rows are gone; active job rows survive.
    for job_id in active_ids:
        assert job_id in remaining_ids
    assert len(remaining) == len(active_ids)
    assert not (swept_job_ids & {j.job_id for j in remaining})


def test_sweep_empty_pass_is_a_no_op(db_session: Session) -> None:
    counts = run_cleanup_pass(db_session)
    assert counts == {"search_sessions": 0, "upload_jobs": 0}


def test_sweep_pass_survives_db_failure(caplog: pytest.LogCaptureFixture) -> None:
    class _BrokenDb:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def exec(self, *args, **kwargs):
            raise RuntimeError("db down")

        def commit(self):
            pass

    with caplog.at_level(logging.WARNING, logger="app.core.cleanup"):
        counts = safe_run_cleanup_pass(lambda: _BrokenDb())

    # The failing pass is swallowed and logged as WARNING; the loop retries.
    assert counts is None
    assert any(rec.levelno == logging.WARNING for rec in caplog.records)


def test_sweep_via_api_lifecycle(
    client: TestClient,
    db_session: Session,
    tmp_upload_root,
) -> None:
    # End-to-end: a finalized session created through the API is swept.
    resp = client.post("/api/v1/sessions")
    session_id = resp.json()["id"]
    from app.crud import get_search_session_by_id

    finalize_search_session(db_session, get_search_session_by_id(db_session, session_id))
    counts = run_cleanup_pass(db_session)
    assert counts["search_sessions"] >= 1
    assert get_search_session_by_id(db_session, session_id) is None
