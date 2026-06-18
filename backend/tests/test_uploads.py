from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings


def _create_job(client: TestClient, expected_count: int = 3) -> str:
    resp = client.post(
        "/api/v1/start_upload",
        json={"expected_image_count": expected_count},
    )
    assert resp.status_code == 201
    return resp.json()["job_id"]


def _upload_batch(
    client: TestClient,
    job_id: str,
    files: list[tuple[str, bytes, str]],
) -> dict:
    return client.post(
        f"/api/v1/uploads/{job_id}/batch",
        files=files,
    )


def _make_image_file(
    name: str = "test.jpg",
    content_type: str = "image/jpeg",
    data: bytes | None = None,
) -> tuple[str, BytesIO, str]:
    if data is None:
        data = b"\xff\xd8\xff" + b"\x00" * 100
    return (name, BytesIO(data), content_type)


# --- Start Upload ---


class TestStartUpload:
    def test_start_upload(self, client: TestClient, tmp_upload_root: Path) -> None:
        resp = client.post(
            "/api/v1/start_upload",
            json={"expected_image_count": 10},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "job_id" in body
        assert body["status"] == "OK"

        job_dir = tmp_upload_root / body["job_id"]
        assert job_dir.exists()
        assert (job_dir / "images").exists()

    def test_start_upload_rejects_zero_count(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/start_upload",
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
        assert body["status"] == "OK"

        resp = client.get(f"/api/v1/uploads/{job_id}")
        assert resp.json()["status"] == "uploaded"

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
        count = settings.MAX_BATCH_IMAGES
        job_id = _create_job(client, expected_count=count)
        files = [_make_image_file(f"img_{i}.jpg") for i in range(count)]
        resp = _upload_batch(client, job_id, files)
        assert resp.status_code == 200
        body = resp.json()
        assert body["failed"] == 0
        assert body["uploaded_count"] == count
