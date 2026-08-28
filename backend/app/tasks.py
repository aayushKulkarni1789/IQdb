import logging
import os
import time
from pathlib import Path

from PIL import Image as PILImage
from sqlmodel import Session

from app.core.clip import get_image_embeddings
from app.core.config import settings
from app.core.db import engine
from app.crud import (
    create_clip_embedding,
    create_image,
    mark_job_completed,
    mark_job_discarded,
    mark_job_processing,
)
from app.search.exif import extract_capture_time, extract_gps

logger = logging.getLogger(__name__)


def _log_ingestion_summary(
    job_id: str, counters: dict[str, int], elapsed: float, status: str
) -> None:
    # One machine-readable summary line per job (ingestion-reporting spec):
    # volume totals, per-field metadata extraction health, timing, terminal status.
    logger.info(
        "Job %s ingestion summary: status=%s total=%d opened_ok=%d written_to_db=%d "
        "file_size=%d dimensions=%d capture_time=%d gps=%d elapsed_seconds=%.2f",
        job_id,
        status,
        counters["total"],
        counters["opened_ok"],
        counters["written_to_db"],
        counters["file_size"],
        counters["dimensions"],
        counters["capture_time"],
        counters["gps"],
        elapsed,
    )


def process_upload_embeddings(job_id: str) -> None:
    logger.info("Starting CLIP embedding ingestion for job %s", job_id)
    images_dir = Path(settings.UPLOAD_ROOT) / job_id / "images"

    if not images_dir.is_dir():
        logger.error("Images directory not found for job %s: %s", job_id, images_dir)
        return

    # NOTE: It is sorted to provide resumability (is that what it's called?)
    image_files = sorted(
        p
        for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
    )
    if not image_files:
        logger.warning("No image files found for job %s", job_id)
        return

    total = len(image_files)
    batch_size = settings.MAX_CLIP_BATCH_IMAGES
    logger.info("Job %s: %d images to process in batches of %d", job_id, total, batch_size)

    start_time = time.monotonic()
    # Summary counters accumulated across batches (design D8). Grouped fields
    # count as extracted only when all constituent columns persist non-NULL.
    counters: dict[str, int] = {
        "total": 0,
        "opened_ok": 0,
        "written_to_db": 0,
        "file_size": 0,
        "dimensions": 0,
        "capture_time": 0,
        "gps": 0,
    }

    try:
        # create a new db session
        with Session(engine) as db:
            job = mark_job_processing(db, job_id)
            if job is None:
                logger.error(
                    "Job %s: failed to transition from UPLOADED to PROCESSING, aborting", job_id
                )
                return

            for start in range(0, total, batch_size):
                batch_files = image_files[start : start + batch_size]
                batch_num = start // batch_size + 1
                total_batches = (total + batch_size - 1) // batch_size
                logger.info(
                    "Job %s: processing batch %d/%d (%d images)",
                    job_id,
                    batch_num,
                    total_batches,
                    len(batch_files),
                )

                pil_images = []
                batch_metadata = []
                for f in batch_files:
                    counters["total"] += 1
                    try:
                        img = PILImage.open(f)
                    except Exception:
                        logger.exception(
                            "Job %s: failed to open image %s, skipping", job_id, f.name
                        )
                        continue
                    pil_images.append(img)
                    counters["opened_ok"] += 1
                    try:
                        file_size = os.fstat(img.fp.fileno()).st_size
                        width, height = img.size
                        capture_time = extract_capture_time(img)
                        gps = extract_gps(img)
                    except Exception:
                        logger.exception(
                            "Job %s: failed to extract metadata from %s", job_id, f.name
                        )
                        file_size, width, height, capture_time = None, None, None, None
                        gps = None
                    latitude, longitude = gps if gps is not None else (None, None)
                    # Count grouped fields only when every constituent column persisted non-NULL.
                    if file_size is not None:
                        counters["file_size"] += 1
                    if width is not None and height is not None:
                        counters["dimensions"] += 1
                    if capture_time is not None:
                        counters["capture_time"] += 1
                    if latitude is not None and longitude is not None:
                        counters["gps"] += 1
                    batch_metadata.append(
                        {
                            "filename": f.name,
                            "file_size": file_size,
                            "width": width,
                            "height": height,
                            "capture_time": capture_time,
                            "latitude": latitude,
                            "longitude": longitude,
                        }
                    )

                if not pil_images:
                    continue

                # Batch process images for getting embeddings
                embeddings = get_image_embeddings(pil_images)

                # Release decoded pixels before any DB writes
                for img in pil_images:
                    img.close()

                # Prepare the table row for Image & CLIP_Embedding table
                pending_written = 0
                for meta, embedding in zip(batch_metadata, embeddings):
                    uri = f"{job_id}/images/{meta['filename']}"
                    image = create_image(
                        db,
                        filename=meta["filename"],
                        uri=uri,
                        width=meta["width"],
                        height=meta["height"],
                        file_size=meta["file_size"],
                        capture_time=meta["capture_time"],
                        latitude=meta["latitude"],
                        longitude=meta["longitude"],
                    )
                    create_clip_embedding(db, image_id=image.id, embedding=embedding)
                    pending_written += 1

                # Only count rows that were actually committed (design D8).
                db.commit()
                counters["written_to_db"] += pending_written
                logger.info("Job %s: batch %d/%d committed", job_id, batch_num, total_batches)

            mark_job_completed(db, job_id)
            _log_ingestion_summary(
                job_id, counters, time.monotonic() - start_time, status="completed"
            )
            logger.info("CLIP embedding ingestion complete for job %s (%d images)", job_id, total)

    except Exception:
        logger.exception("Job %s: processing failed unexpectedly", job_id)
        # Partial summary before termination (ingestion-reporting spec): the
        # record of how far the job got must survive the failure.
        _log_ingestion_summary(job_id, counters, time.monotonic() - start_time, status="failed")
        try:
            with Session(engine) as db:
                mark_job_discarded(db, job_id)
        except Exception:
            logger.exception("Job %s: failed to mark job as discarded after error", job_id)
