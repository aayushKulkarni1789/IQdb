import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.api.deps import SessionDep
from app.core.config import settings
from app.crud import (
    create_upload_job,
    finalize_batch,
    get_upload_job_by_job_id,
    mark_job_uploaded,
    transition_to_uploading,
)
from app.models import (
    BatchUploadResponse,
    CompleteUploadResponse,
    StartUploadRequest,
    StartUploadResponse,
    UploadJobPublic,
    UploadJobStatus,
)

from typing import Annotated

from pydantic.json_schema import WithJsonSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])


# Start an upload
@router.post("/start", response_model=StartUploadResponse)
def start_upload(
    body: StartUploadRequest,
    db: SessionDep,
) -> StartUploadResponse:
    job = create_upload_job(db, body.expected_image_count)
    return StartUploadResponse(job_id=job.job_id, status=job.status)


@router.get("/{job_id}", response_model=UploadJobPublic)
def get_upload_status(
    job_id: str,
    db: SessionDep,
) -> UploadJobPublic:
    job = get_upload_job_by_job_id(db, job_id)
    if not job:
        logger.warning("Upload job not found: %s", job_id)
        raise HTTPException(status_code=404, detail="Upload job not found")
    return UploadJobPublic(
        job_id=job.job_id,
        status=job.status,
        expected_image_count=job.expected_image_count,
        uploaded_count=job.uploaded_count,
        created_at=job.created_at,
    )


@router.post("/{job_id}/batch", response_model=BatchUploadResponse)
async def batch_upload(
    job_id: str,
    images: Annotated[
        list[UploadFile],
        File(),
        WithJsonSchema({
            "type": "array",
            "items": {
                "type": "string",
                "format": "binary",
            }})], # weird bug
    db: SessionDep,
) -> BatchUploadResponse:
    job = get_upload_job_by_job_id(db, job_id)
    if not job:
        logger.warning("Upload job not found: %s", job_id)
        raise HTTPException(status_code=404, detail="Upload job not found")

    if job.status not in {UploadJobStatus.OPEN, UploadJobStatus.UPLOADING}:
        logger.warning(
            "Upload job %s in invalid state for batch upload: %s",
            job_id,
            job.status,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Upload job is in invalid state: {job.status}",
        )

    if job.status == UploadJobStatus.OPEN:
        job = transition_to_uploading(db, job_id)
        if job is None:
            logger.warning("Upload job not found after transition: %s", job_id)
            raise HTTPException(status_code=404, detail="Upload job not found")
        if job.status != UploadJobStatus.UPLOADING:
            logger.warning(
                "Upload job %s failed to transition to uploading, status=%s",
                job_id,
                job.status,
            )
            raise HTTPException(
                status_code=409,
                detail="Upload job failed to transition to uploading",
            )

    if len(images) > settings.MAX_BATCH_IMAGES:
        logger.warning(
            "Upload job %s batch exceeds maximum of %s images (got %s)",
            job_id,
            settings.MAX_BATCH_IMAGES,
            len(images),
        )
        raise HTTPException(
            status_code=400,
            detail=f"Batch exceeds maximum of {settings.MAX_BATCH_IMAGES} images",
        )

    if len(images) == 0:
        logger.warning("Upload job %s received empty batch", job_id)
        raise HTTPException(
            status_code=400,
            detail="Batch must contain at least one image",
        )

    if job.uploaded_count + len(images) > job.expected_image_count:
        logger.warning(
            "Upload job %s batch would exceed expected count: "
            "uploaded=%s, attempted=%s, expected=%s",
            job_id,
            job.uploaded_count,
            len(images),
            job.expected_image_count,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"Batch would exceed expected image count: "
                f"uploaded_count={job.uploaded_count}, "
                f"attempted={len(images)}, "
                f"expected_image_count={job.expected_image_count}"
            ),
        )

    images_dir = Path(settings.UPLOAD_ROOT) / job_id / "images"
    max_size_bytes = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    resolved_images_dir = images_dir.resolve()

    success_count = 0
    failed_count = 0
    next_seq = job.uploaded_count + 1

    for i, file in enumerate(images):
        if not file.content_type or not file.content_type.startswith("image/"):
            logger.warning(
                "Upload job %s file %s: rejected content_type=%r",
                job_id,
                i,
                file.content_type,
            )
            failed_count += 1
            continue

        safe_name = Path(file.filename or "upload").name
        if safe_name in {"", ".", ".."}:
            logger.warning(
                "Upload job %s file %s: invalid filename %r",
                job_id,
                i,
                file.filename,
            )
            failed_count += 1
            continue

        filename = f"{next_seq + i:03d}_{safe_name}"
        dest_path = images_dir / filename

        if not dest_path.resolve().is_relative_to(resolved_images_dir):
            logger.warning(
                "Upload job %s file %s: path escapes upload directory: %r",
                job_id,
                i,
                file.filename,
            )
            failed_count += 1
            continue

        try:
            content = await file.read()
            if len(content) > max_size_bytes:
                logger.warning(
                    "Upload job %s file %s (%s): exceeds %sMB limit",
                    job_id,
                    i,
                    safe_name,
                    settings.MAX_IMAGE_SIZE_MB,
                )
                failed_count += 1
                continue
            dest_path.write_bytes(content)
            success_count += 1
        except Exception:
            dest_path.unlink(missing_ok=True)
            logger.exception(
                "Upload job %s file %s (%s): failed to save",
                job_id,
                i,
                safe_name,
            )
            failed_count += 1

    job = finalize_batch(db, job_id, success_count)
    if job is None:
        logger.warning("Upload job not found after finalize_batch: %s", job_id)
        raise HTTPException(status_code=404, detail="Upload job not found")

    return BatchUploadResponse(
        failed=failed_count,
        uploaded_count=job.uploaded_count,
    )


@router.post("/{job_id}/complete", response_model=CompleteUploadResponse)
def complete_upload(
    job_id: str,
    db: SessionDep,
) -> CompleteUploadResponse:
    job = get_upload_job_by_job_id(db, job_id)
    if not job:
        logger.warning("Upload job not found: %s", job_id)
        raise HTTPException(status_code=404, detail="Upload job not found")

    if job.status != UploadJobStatus.UPLOADING:
        logger.warning(
            "Upload job %s complete rejected: not in uploading state (status=%s)",
            job_id,
            job.status,
        )
        raise HTTPException(
            status_code=400,
            detail="Upload job is not in uploading state",
        )

    if job.uploaded_count != job.expected_image_count:
        logger.warning(
            "Upload job %s complete rejected: uploaded_count=%s, expected=%s",
            job_id,
            job.uploaded_count,
            job.expected_image_count,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                f"uploaded_count ({job.uploaded_count}) does not match "
                f"expected_image_count ({job.expected_image_count})"
            ),
        )

    job = mark_job_uploaded(db, job_id)
    if job is None:
        logger.warning("Upload job not found after mark_job_uploaded: %s", job_id)
        raise HTTPException(status_code=404, detail="Upload job not found")
    if job.status != UploadJobStatus.UPLOADED:
        logger.warning(
            "Upload job %s failed to transition to uploaded, status=%s",
            job_id,
            job.status,
        )
        raise HTTPException(
            status_code=409,
            detail="Upload job failed to transition to uploaded",
        )

    return CompleteUploadResponse(job_id=job.job_id, status=job.status)
