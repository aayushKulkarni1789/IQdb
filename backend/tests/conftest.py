import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, SQLModel

from app.core.config import settings
from app.core.db import engine
from app.crud import create_clip_embedding, create_image
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Generator:
    SQLModel.metadata.create_all(engine)
    yield


@pytest.fixture(name="db_session")
def db_session() -> Generator:
    with Session(engine) as session:
        yield session
        session.rollback()
        session.exec(
            text(
                "TRUNCATE TABLE searchsession, clip_embedding, image, uploadjob "
                "RESTART IDENTITY CASCADE;"
            )
        )
        session.commit()


@pytest.fixture(name="client")
def client(db_session: Session) -> Generator:
    from app.api.deps import get_db

    def _get_db_override() -> Generator:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(name="tmp_upload_root")
def tmp_upload_root() -> Generator:
    tmp_dir = Path(tempfile.mkdtemp())
    original = settings.UPLOAD_ROOT
    settings.UPLOAD_ROOT = str(tmp_dir)
    yield tmp_dir
    settings.UPLOAD_ROOT = original
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(name="sample_image_bytes")
def sample_image_bytes() -> bytes:
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.\x27 \",#\x1c\x1c(7),01444\x1f'9=82<.342"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\x9e\x97\xfa\xce"
        b"\xff\xd9"
    )


def seed_images(db_session: Session, n: int) -> list[int]:
    ids: list[int] = []
    for i in range(n):
        img = create_image(
            db_session,
            filename=f"seed_{i}.jpg",
            uri=f"/seed_{i}.jpg",
        )
        create_clip_embedding(
            db_session,
            image_id=img.id,
            embedding=[1.0 if i == k else 0.0 for k in range(512)],
        )
        ids.append(img.id)
    db_session.commit()
    return ids
