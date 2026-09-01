from datetime import datetime, timezone, timedelta
from io import BytesIO
from pathlib import Path

import logging

import pytest
from fastapi.testclient import TestClient
from PIL import Image as PILImage
from sqlmodel import Session, select

from app.core.clip import get_image_embeddings
from app.core.config import settings
from app.models import Image, UploadJob, UploadJobStatus


def _create_job(client: TestClient, expected_count: int = 3) -> str:
    resp = client.post(
        "/api/v1/uploads/start",
        json={"expected_image_count": expected_count},
    )
    assert resp.status_code == 201
    return resp.json()["job_id"]


def _upload_batch(
    client: TestClient,
    job_id: str,
    files: list[tuple[str, BytesIO, str]],
) -> dict:
    return client.post(
        f"/api/v1/uploads/{job_id}/batch",
        files=[("images", (name, data, ct)) for (name, data, ct) in files],
    )


def _make_image_file(
    name: str = "test.jpg",
    content_type: str = "image/jpeg",
    data: bytes | None = None,
) -> tuple[str, BytesIO, str]:
    if data is None:
        data = b"\xff\xd8\xff" + b"\x00" * 100
    return (name, BytesIO(data), content_type)


def _make_exif_image_file(
    name: str = "exif.jpg",
    datetime_str: str = "2024:06:15 14:30:00",
    offset_str: str = "+05:30",
) -> tuple[str, BytesIO, str]:
    img = PILImage.new("RGB", (4, 4))
    exif = PILImage.Exif()
    exif_ifd = exif.get_ifd(0x8769)
    exif_ifd[0x9003] = datetime_str
    exif_ifd[0x9011] = offset_str
    exif_ifd[0x9004] = datetime_str
    exif_ifd[0x9012] = offset_str
    gps = exif.get_ifd(0x8825)
    gps[0x0001] = "N"
    gps[0x0002] = (40, 30, 0)
    gps[0x0003] = "W"
    gps[0x0004] = (74, 0, 0)
    buf = BytesIO()
    img.save(buf, "JPEG", exif=exif.tobytes())
    return (name, BytesIO(buf.getvalue()), "image/jpeg")


# --- Start Upload ---


class TestStartUpload:
    def test_start_upload(self, client: TestClient, tmp_upload_root: Path) -> None:
        resp = client.post(
            "/api/v1/uploads/start",
            json={"expected_image_count": 10},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "job_id" in body
        assert body["status"] == "open"

        job_dir = tmp_upload_root / body["job_id"]
        assert job_dir.exists()
        assert (job_dir / "images").exists()

    def test_start_upload_rejects_zero_count(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/uploads/start",
            json={"expected_image_count": 0},
        )
        assert resp.status_code == 422


# --- Get Status ---


class TestGetStatus:
    def test_get_status(self, client: TestClient, tmp_upload_root: Path) -> None:
        job_id = _create_job(client)
        resp = client.get(f"/api/v1/uploads/{job_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["job_id"] == job_id
        assert body["status"] == "open"
        assert body["expected_image_count"] == 3
        assert body["uploaded_count"] == 0
        assert "created_at" in body

    def test_get_status_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/uploads/nonexistent")
        assert resp.status_code == 404


# --- Batch Upload ---


class TestBatchUpload:
    def test_batch_single_image(
        self,
        client: TestClient,
        tmp_upload_root: Path,
    ) -> None:
        job_id = _create_job(client, expected_count=1)
        files = [_make_image_file("photo.jpg")]
        resp = _upload_batch(client, job_id, files)
        assert resp.status_code == 200
        body = resp.json()
        assert body["failed"] == 0
        assert body["uploaded_count"] == 1

        images_dir = tmp_upload_root / job_id / "images"
        saved = list(images_dir.iterdir())
        assert len(saved) == 1
        assert saved[0].name == "001_photo.jpg"

    def test_batch_multiple_images(
        self,
        client: TestClient,
        tmp_upload_root: Path,
    ) -> None:
        job_id = _create_job(client, expected_count=3)
        files = [
            _make_image_file("a.jpg"),
            _make_image_file("b.png", "image/png"),
            _make_image_file("c.jpg"),
        ]
        resp = _upload_batch(client, job_id, files)
        assert resp.status_code == 200
        body = resp.json()
        assert body["failed"] == 0
        assert body["uploaded_count"] == 3

        images_dir = tmp_upload_root / job_id / "images"
        saved = sorted(images_dir.iterdir())
        assert [f.name for f in saved] == ["001_a.jpg", "002_b.png", "003_c.jpg"]

    def test_batch_rejects_non_image(
        self,
        client: TestClient,
        tmp_upload_root: Path,
    ) -> None:
        job_id = _create_job(client)
        files = [("file.txt", BytesIO(b"not an image"), "text/plain")]
        resp = _upload_batch(client, job_id, files)
        assert resp.status_code == 200
        body = resp.json()
        assert body["failed"] == 1
        assert body["uploaded_count"] == 0

    def test_batch_404_nonexistent_job(self, client: TestClient) -> None:
        files = [_make_image_file("photo.jpg")]
        resp = _upload_batch(client, "nonexistent", files)
        assert resp.status_code == 404

    def test_batch_rejects_finalized_job(
        self,
        client: TestClient,
        tmp_upload_root: Path,
    ) -> None:
        job_id = _create_job(client, expected_count=1)
        files = [_make_image_file("photo.jpg")]
        _upload_batch(client, job_id, files)
        client.post(f"/api/v1/uploads/{job_id}/complete")

        resp = _upload_batch(client, job_id, [_make_image_file("extra.jpg")])
        assert resp.status_code == 400

    def test_first_batch_transitions_to_uploading(
        self,
        client: TestClient,
        tmp_upload_root: Path,
    ) -> None:
        job_id = _create_job(client, expected_count=1)
        resp = client.get(f"/api/v1/uploads/{job_id}")
        assert resp.json()["status"] == "open"

        _upload_batch(client, job_id, [_make_image_file("a.jpg")])

        resp = client.get(f"/api/v1/uploads/{job_id}")
        assert resp.json()["status"] == "uploading"


# --- Resume Upload ---


class TestResumeUpload:
    def test_resume_upload(
        self,
        client: TestClient,
        tmp_upload_root: Path,
    ) -> None:
        job_id = _create_job(client, expected_count=4)

        _upload_batch(client, job_id, [_make_image_file("a.jpg")])
        _upload_batch(client, job_id, [_make_image_file("b.jpg")])

        resp = client.get(f"/api/v1/uploads/{job_id}")
        body = resp.json()
        assert body["uploaded_count"] == 2
        assert body["status"] == "uploading"

        images_dir = tmp_upload_root / job_id / "images"
        saved = sorted(images_dir.iterdir())
        assert [f.name for f in saved] == ["001_a.jpg", "002_b.jpg"]


# --- Complete Upload ---


class TestCompleteUpload:
    def test_complete_upload(
        self,
        client: TestClient,
        tmp_upload_root: Path,
    ) -> None:
        job_id = _create_job(client, expected_count=2)
        _upload_batch(
            client,
            job_id,
            [_make_image_file("a.jpg"), _make_image_file("b.jpg")],
        )
        resp = client.post(f"/api/v1/uploads/{job_id}/complete")
        assert resp.status_code == 200
        body = resp.json()
        assert body["job_id"] == job_id
        assert body["status"] == "uploaded"

        resp = client.get(f"/api/v1/uploads/{job_id}")
        assert resp.json()["status"] == "completed"

    def test_complete_rejects_count_mismatch(
        self,
        client: TestClient,
        tmp_upload_root: Path,
    ) -> None:
        job_id = _create_job(client, expected_count=5)
        _upload_batch(client, job_id, [_make_image_file("a.jpg")])
        resp = client.post(f"/api/v1/uploads/{job_id}/complete")
        assert resp.status_code == 400

    def test_complete_rejects_open_job(
        self,
        client: TestClient,
        tmp_upload_root: Path,
    ) -> None:
        job_id = _create_job(client, expected_count=1)
        resp = client.post(f"/api/v1/uploads/{job_id}/complete")
        assert resp.status_code == 400


# --- Large Batch ---


class TestLargeBatch:
    def test_large_batch(
        self,
        client: TestClient,
        tmp_upload_root: Path,
    ) -> None:
        count = settings.MAX_UPLOAD_BATCH_IMAGES
        job_id = _create_job(client, expected_count=count)
        files = [_make_image_file(f"img_{i}.jpg") for i in range(count)]
        resp = _upload_batch(client, job_id, files)
        assert resp.status_code == 200
        body = resp.json()
        assert body["failed"] == 0
        assert body["uploaded_count"] == count


# --- EXIF Integration ---


class TestExifIngestion:
    def test_exif_data_stored_on_upload(
        self,
        client: TestClient,
        db_session: Session,
        tmp_upload_root: Path,
    ) -> None:
        job_id = _create_job(client, expected_count=1)
        files = [_make_exif_image_file("exif_test.jpg")]
        resp = _upload_batch(client, job_id, files)
        assert resp.status_code == 200

        resp = client.post(f"/api/v1/uploads/{job_id}/complete")
        assert resp.status_code == 200

        image = db_session.exec(select(Image)).first()
        assert image is not None
        assert image.capture_time is not None
        # capture_time is stored as naive local time (ADR-0005) - offset is dropped
        expected = datetime(2024, 6, 15, 14, 30, 0)
        assert image.capture_time == expected
        assert image.latitude is not None
        assert abs(image.latitude - 40.5) < 0.001
        assert image.longitude is not None
        assert abs(image.longitude - (-74.0)) < 0.001


# --- Corrupt File Batch ---


class TestCorruptBatchIngestion:
    def test_batch_with_corrupt_file_keeps_embeddings_aligned(
        self,
        client: TestClient,
        db_session: Session,
        tmp_upload_root: Path,
    ) -> None:
        job_id = _create_job(client, expected_count=3)
        corrupt = _make_image_file("corrupt.jpg", data=b"not really a jpeg")
        exif_a = _make_exif_image_file("a.jpg")
        exif_b = _make_exif_image_file(
            "b.jpg",
            datetime_str="2023:01:01 08:00:00",
            offset_str="+00:00",
        )
        resp = _upload_batch(client, job_id, [corrupt, exif_a, exif_b])
        assert resp.status_code == 200
        assert resp.json()["failed"] == 0

        resp = client.post(f"/api/v1/uploads/{job_id}/complete")
        assert resp.status_code == 200

        images = db_session.exec(select(Image).order_by(Image.filename)).all()
        assert len(images) == 2
        by_name = {img.filename: img for img in images}
        # capture_time is stored as naive local time (ADR-0005) - offset is dropped
        assert by_name["002_a.jpg"].capture_time == datetime(2024, 6, 15, 14, 30, 0)
        assert by_name["003_b.jpg"].capture_time == datetime(2023, 1, 1, 8, 0, 0)

        images_dir = tmp_upload_root / job_id / "images"
        valid_files = sorted(p for p in images_dir.iterdir() if p.name != "001_corrupt.jpg")
        assert [p.name for p in valid_files] == ["002_a.jpg", "003_b.jpg"]
        references = get_image_embeddings([PILImage.open(p) for p in valid_files])
        for img, ref in zip(images, references):
            assert img.clip_embedding is not None
            assert list(img.clip_embedding.embedding) == pytest.approx(ref)


# --- Ingestion Summary Logging ---


def _seed_job_files(
    db_session: Session,
    tmp_upload_root: Path,
    files: list[tuple[str, bytes]],
) -> str:
    """Insert an UPLOADED job row and write its image files to disk."""
    import uuid

    job_id = uuid.uuid4().hex
    images_dir = Path(tmp_upload_root) / job_id / "images"
    images_dir.mkdir(parents=True)
    for name, data in files:
        (images_dir / name).write_bytes(data)

    job = UploadJob(job_id=job_id, expected_image_count=len(files), status=UploadJobStatus.UPLOADED)
    db_session.add(job)
    db_session.commit()
    return job_id


def _jpeg_bytes(width: int = 4, height: int = 4, exif: PILImage.Exif | None = None) -> bytes:
    img = PILImage.new("RGB", (width, height))
    buf = BytesIO()
    if exif is not None:
        img.save(buf, "JPEG", exif=exif.tobytes())
    else:
        img.save(buf, "JPEG")
    return buf.getvalue()


def _last_summary_record(caplog: pytest.LogCaptureFixture) -> logging.LogRecord:
    summaries = [
        rec
        for rec in caplog.records
        if rec.name == "app.tasks" and "ingestion summary" in rec.getMessage()
    ]
    assert summaries, "expected an ingestion summary log line"
    return summaries[-1]


class TestIngestionSummary:
    def test_successful_job_logs_full_summary(
        self,
        db_session: Session,
        tmp_upload_root: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # One EXIF-complete image, one plain image without metadata, one
        # unreadable file: total counts it, opened_ok/written exclude it.
        import app.tasks as tasks_module

        monkeypatch.setattr(
            tasks_module, "get_image_embeddings", lambda imgs: [[0.0] * 512 for _ in imgs]
        )

        files = [
            ("exif.jpg", _make_exif_image_file("exif.jpg")[1].getvalue()),
            ("plain.jpg", _jpeg_bytes()),
            ("corrupt.jpg", b"not really a jpeg"),
        ]
        job_id = _seed_job_files(db_session, tmp_upload_root, files)

        with caplog.at_level(logging.INFO, logger="app.tasks"):
            tasks_module.process_upload_embeddings(job_id)

        msg = _last_summary_record(caplog).getMessage()
        assert "status=completed" in msg
        assert "total=3" in msg
        assert "opened_ok=2" in msg
        assert "written_to_db=2" in msg
        assert "file_size=2" in msg
        assert "dimensions=2" in msg
        assert "capture_time=1" in msg
        assert "gps=1" in msg
        assert "elapsed_seconds=" in msg

    def test_grouped_fields_require_all_constituents(
        self,
        db_session: Session,
        tmp_upload_root: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import app.tasks as tasks_module

        monkeypatch.setattr(
            tasks_module, "get_image_embeddings", lambda imgs: [[0.0] * 512 for _ in imgs]
        )
        # GPS with latitude but no longitude must NOT count; capture time does.
        monkeypatch.setattr(tasks_module, "extract_gps", lambda img: (40.5, None))
        from datetime import datetime as dt

        monkeypatch.setattr(
            tasks_module, "extract_capture_time", lambda img: dt(2024, 1, 1, tzinfo=timezone.utc)
        )

        files = [("plain.jpg", _jpeg_bytes())]
        job_id = _seed_job_files(db_session, tmp_upload_root, files)

        with caplog.at_level(logging.INFO, logger="app.tasks"):
            tasks_module.process_upload_embeddings(job_id)

        msg = _last_summary_record(caplog).getMessage()
        assert "gps=0" in msg
        assert "capture_time=1" in msg
        assert "status=completed" in msg

    def test_failed_job_logs_partial_summary(
        self,
        db_session: Session,
        tmp_upload_root: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import app.tasks as tasks_module

        def _explode(imgs):
            raise RuntimeError("embedding backend exploded")

        monkeypatch.setattr(tasks_module, "get_image_embeddings", _explode)

        files = [("a.jpg", _jpeg_bytes()), ("b.jpg", _jpeg_bytes())]
        job_id = _seed_job_files(db_session, tmp_upload_root, files)

        with caplog.at_level(logging.INFO, logger="app.tasks"):
            tasks_module.process_upload_embeddings(job_id)

        msg = _last_summary_record(caplog).getMessage()
        assert "status=failed" in msg
        assert "total=2" in msg
        assert "opened_ok=2" in msg
        assert "written_to_db=0" in msg

        # The job is still marked discarded after the failure.
        job = db_session.exec(select(UploadJob).where(UploadJob.job_id == job_id)).one()
        assert job.status == UploadJobStatus.DISCARD
