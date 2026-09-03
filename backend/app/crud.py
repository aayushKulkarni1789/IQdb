from datetime import datetime
import uuid
from pathlib import Path

from sqlalchemy import update
from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    CLIP_Embedding,
    Image,
    SearchSession,
    UploadJob,
    UploadJobStatus,
)


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
        if job.status == UploadJobStatus.UPLOADED:  # if it is already uploaded
            return job
        return None
    return job


def mark_job_discarded(
    db: Session,
    job_id: str,
) -> UploadJob | None:
    result = db.exec(
        update(UploadJob)
        .where(UploadJob.job_id == job_id, UploadJob.status != UploadJobStatus.DISCARD)
        .values(status=UploadJobStatus.DISCARD)
    )
    db.commit()
    job = get_upload_job_by_job_id(db, job_id)
    if job is None:
        return None
    if result.rowcount == 0:
        if job.status == UploadJobStatus.DISCARD:  # if it is already aborted/failed
            return job
        return None
    return job


def mark_job_processing(
    db: Session,
    job_id: str,
) -> UploadJob | None:
    result = db.exec(
        update(UploadJob)
        .where(UploadJob.job_id == job_id, UploadJob.status == UploadJobStatus.UPLOADED)
        .values(status=UploadJobStatus.PROCESSING)
    )
    db.commit()
    job = get_upload_job_by_job_id(db, job_id)
    if job is None:
        return None
    if result.rowcount == 0:
        if job.status == UploadJobStatus.PROCESSING:
            return job
        return None
    return job


def mark_job_completed(
    db: Session,
    job_id: str,
) -> UploadJob | None:
    result = db.exec(
        update(UploadJob)
        .where(UploadJob.job_id == job_id, UploadJob.status == UploadJobStatus.PROCESSING)
        .values(status=UploadJobStatus.COMPLETED)
    )
    db.commit()
    job = get_upload_job_by_job_id(db, job_id)
    if job is None:
        return None
    if result.rowcount == 0:
        if job.status == UploadJobStatus.COMPLETED:
            return job
        return None
    return job


def create_image(
    db: Session,
    filename: str,
    uri: str,
    width: int | None = None,
    height: int | None = None,
    file_size: int | None = None,
    capture_time: datetime | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> Image:
    location = (
        f"SRID=4326;POINT({longitude} {latitude})"
        if latitude is not None and longitude is not None
        else None
    )
    image = Image(
        filename=filename,
        uri=uri,
        width=width,
        height=height,
        file_size=file_size,
        capture_time=capture_time,
        latitude=latitude,
        longitude=longitude,
        location=location,
    )
    db.add(image)
    db.flush()
    db.refresh(image)
    return image


def create_clip_embedding(
    db: Session,
    image_id: int,
    embedding: list[float],
) -> CLIP_Embedding:
    clip_embedding = CLIP_Embedding(
        image_id=image_id,
        embedding=embedding,
    )
    db.add(clip_embedding)
    db.flush()
    db.refresh(clip_embedding)
    return clip_embedding


def create_search_session(db: Session) -> SearchSession:
    session = SearchSession(specs=[], finalized=False)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_search_session_by_id(
    db: Session,
    session_id: int,
) -> SearchSession | None:
    return db.exec(select(SearchSession).where(SearchSession.id == session_id)).first()


def append_filter_spec(
    db: Session,
    session: SearchSession,
    spec: dict,
) -> SearchSession:
    session.specs = list(session.specs) + [spec]
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def finalize_search_session(
    db: Session,
    session: SearchSession,
) -> SearchSession:
    session.finalized = True
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
