import logging

from sqlalchemy import delete
from sqlmodel import Session

from app.models import SearchSession, UploadJob, UploadJobStatus

logger = logging.getLogger(__name__)

# Terminal upload-job statuses eligible for sweeping: finalize/completion is
# treated as terminal — no retention-age check applies (design D2).
_TERMINAL_JOB_STATUSES = (UploadJobStatus.COMPLETED, UploadJobStatus.DISCARD)


def run_cleanup_pass(db: Session) -> dict[str, int]:
    """Delete every finalized ``SearchSession`` and every terminal ``UploadJob``.

    A plain callable so tests can invoke it directly without waiting on the
    timer loop (design D3). Deletes are unconditional and idempotent: a missed
    or repeated pass converges to the same DB state.
    """
    sessions_result = db.exec(delete(SearchSession).where(SearchSession.finalized == True))  # noqa: E712
    jobs_result = db.exec(delete(UploadJob).where(UploadJob.status.in_(_TERMINAL_JOB_STATUSES)))
    db.commit()

    counts = {
        "search_sessions": sessions_result.rowcount or 0,
        "upload_jobs": jobs_result.rowcount or 0,
    }

    # NOTE (future work): physical deletion of UPLOAD_ROOT/<job_id>/ is coded
    # but deliberately disabled (needs `shutil`, `Path`, and `settings` imports).
    # Concurrent workers could race on directory deletion (deleting files for a
    # job another worker is still writing), so enabling disk cleanup requires a
    # multi-worker coordination decision first — see design.md Non-Goals and ADR-0004.
    #
    # for job_id in deleted_job_ids:
    #     shutil.rmtree(Path(settings.UPLOAD_ROOT) / job_id, ignore_errors=True)

    if counts["search_sessions"] or counts["upload_jobs"]:
        logger.info(
            "Cleanup sweep pass deleted %d finalized search session(s) and %d terminal upload job(s)",
            counts["search_sessions"],
            counts["upload_jobs"],
        )
    else:
        logger.debug("Cleanup sweep pass found nothing to delete")

    return counts


def safe_run_cleanup_pass(session_factory) -> dict[str, int] | None:
    """Run one sweep pass, swallowing and logging any database failure.

    Used by the background loop so an outage delays sweeping without ever
    crashing the backend; the next tick retries (design D3).
    """
    try:
        with session_factory() as db:
            return run_cleanup_pass(db)
    except Exception:
        logger.warning("Cleanup sweep pass failed; will retry next tick", exc_info=True)
        return None
