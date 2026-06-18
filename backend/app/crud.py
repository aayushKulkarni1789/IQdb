import uuid
from pathlib import Path

from sqlalchemy import update
from sqlmodel import Session, select

from app.core.config import settings
from app.models import UploadJob, UploadJobStatus


def create_upload_job(
    db: Session,
    expected_image_count: int,
) -> UploadJob:
    job_id = uuid.uuid4().hex
    upload_dir = Path(settings.UPLOAD_ROOT) / job_id / "images"
    upload_dir.mkdir(parents=True, exist_ok=True)

    job = UploadJob(
        job_id=job_id,
        expected_image_count=expected_image_count,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_upload_job_by_job_id(
    db: Session,
    job_id: str,
) -> UploadJob | None:
    return db.exec(select(UploadJob).where(UploadJob.job_id == job_id)).first()


def finalize_batch(
    db: Session,
    job_id: str,
    success_count: int,
) -> UploadJob | None:
    db.exec(
        update(UploadJob)
        .where(UploadJob.job_id == job_id)
        .values(uploaded_count=UploadJob.uploaded_count + success_count)
    )
    db.commit()
    return get_upload_job_by_job_id(db, job_id)


def transition_to_uploading(
    db: Session,
    job_id: str,
) -> UploadJob | None:
    result = db.exec(
        update(UploadJob)
        .where(UploadJob.job_id == job_id, UploadJob.status == UploadJobStatus.OPEN)
        .values(status=UploadJobStatus.UPLOADING)
    )
    db.commit()
    job = get_upload_job_by_job_id(db, job_id)
    if job is None:
        return None
    if result.rowcount == 0:
        if job.status == UploadJobStatus.UPLOADING:
            return job
        return None
    return job


def mark_job_uploaded(
    db: Session,
    job_id: str,
) -> UploadJob | None:
    result = db.exec(
        update(UploadJob)
        .where(UploadJob.job_id == job_id, UploadJob.status == UploadJobStatus.UPLOADING)
        .values(status=UploadJobStatus.UPLOADED)
    )
    db.commit()
    job = get_upload_job_by_job_id(db, job_id)
    if job is None:
        return None
    if result.rowcount == 0:
        if job.status == UploadJobStatus.UPLOADED:
            return job
        return None
    return job
