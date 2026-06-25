from pathlib import Path

import requests


class ImgDbClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()

    def create_session(self, expected_count: int) -> tuple[str, str]:
        resp = self._session.post(
            f"{self.base_url}/api/v1/uploads/start",
            json={"expected_image_count": expected_count},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["job_id"], data["status"]

    def upload_batch(self, job_id: str, files: list[Path]) -> dict:
        upload_files = []
        for f in files:
            upload_files.append(("images", (f.name, f.read_bytes(), _guess_mime(f))))
        resp = self._session.post(
            f"{self.base_url}/api/v1/uploads/{job_id}/batch",
            files=upload_files,
        )
        resp.raise_for_status()
        return resp.json()

    def get_status(self, job_id: str) -> dict:
        resp = self._session.get(f"{self.base_url}/api/v1/uploads/{job_id}")
        resp.raise_for_status()
        return resp.json()

    def complete(self, job_id: str) -> dict:
        resp = self._session.post(f"{self.base_url}/api/v1/uploads/{job_id}/complete")
        resp.raise_for_status()
        return resp.json()


def _guess_mime(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }.get(ext, "application/octet-stream")
