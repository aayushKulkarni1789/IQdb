import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.core.config import settings
from app.main import app


@pytest.fixture(name="db_engine")
def db_engine() -> Generator:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="db_session")
def db_session(db_engine) -> Generator:
    with Session(db_engine) as session:
        yield session


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
    # Minimal valid JPEG: 1x1 white pixel
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
