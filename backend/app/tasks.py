import logging
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
                for f in batch_files:
                    try:
                        pil_images.append(PILImage.open(f))
                    except Exception:
                        logger.exception(
                            "Job %s: failed to open image %s, skipping", job_id, f.name
                        )

                if not pil_images:
                    continue

                # Batch process images for getting embeddings
                embeddings = get_image_embeddings(pil_images)

                # Prepare the table row for Image & CLIP_Embedding table
                for f, embedding in zip(batch_files, embeddings):
                    file_size = f.stat().st_size
                    width, height = None, None
                    capture_time = None
                    latitude = None
                    longitude = None
                    try:
                        with PILImage.open(f) as img:
                            width, height = img.size
                            capture_time = extract_capture_time(img)
                            gps = extract_gps(img)
                            if gps is not None:
                                latitude, longitude = gps
                    except Exception:
                        logger.exception(
                            "Job %s: failed to extract metadata from %s", job_id, f.name
                        )

                    uri = f"{job_id}/images/{f.name}"
                    image = create_image(
                        db,
                        filename=f.name,
                        uri=uri,
                        width=width,
                        height=height,
                        file_size=file_size,
                        capture_time=capture_time,
                        latitude=latitude,
                        longitude=longitude,
                    )
                    create_clip_embedding(db, image_id=image.id, embedding=embedding)

                db.commit()
                for img in pil_images:
                    img.close()
                logger.info("Job %s: batch %d/%d committed", job_id, batch_num, total_batches)

            mark_job_completed(db, job_id)
            logger.info("CLIP embedding ingestion complete for job %s (%d images)", job_id, total)

    except Exception:
        logger.exception("Job %s: processing failed unexpectedly", job_id)
        try:
            with Session(engine) as db:
                mark_job_discarded(db, job_id)
        except Exception:
            logger.exception("Job %s: failed to mark job as discarded after error", job_id)
