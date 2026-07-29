from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Index, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# --- Enums ---


class UploadJobStatus(StrEnum):
    OPEN = "open"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DISCARD = "discard"


# --- Base (shared fields) ---


class ImageBase(SQLModel):
    filename: str
    uri: str
    width: int | None = None
    height: int | None = None
    file_size: int | None = None


# --- API input schemas ---


class ImageCreate(ImageBase):
    pass


class ImageUpdate(SQLModel):
    filename: str | None = None
    uri: str | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None


class StartUploadRequest(SQLModel):
    expected_image_count: int = Field(ge=1)


# --- API response schemas ---


class ImagePublic(ImageBase):
    id: int
    uploaded_at: datetime | None = None
    capture_time: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None


class ImagesPublic(SQLModel):
    data: list[ImagePublic]
    count: int


class BatchUploadResponse(SQLModel):
    failed: int = Field(ge=0)
    uploaded_count: int = Field(ge=0)


class UploadStatusChangeResponse(SQLModel):
    job_id: str
    status: UploadJobStatus


class UploadJobPublic(SQLModel):
    job_id: str
    status: UploadJobStatus
    expected_image_count: int
    uploaded_count: int
    created_at: datetime | None = None


# --- Database tables ---


class Image(ImageBase, table=True):
    uri: str = Field(unique=True)
    id: int | None = Field(default=None, primary_key=True)
    uploaded_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    capture_time: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)
    clip_embedding: Optional["CLIP_Embedding"] = Relationship(back_populates="image")


class CLIP_Embedding(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    image_id: int = Field(foreign_key="image.id", unique=True)
    embedding: Any = Field(sa_type=VECTOR(512))
    image: Image | None = Relationship(back_populates="clip_embedding")

    __table_args__ = (
        Index(
            "ix_clip_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class UploadJob(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_id: str = Field(unique=True, index=True)
    status: UploadJobStatus = Field(default=UploadJobStatus.OPEN, sa_type=String())
    expected_image_count: int = Field(ge=1)
    uploaded_count: int = Field(default=0, ge=0)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class SearchSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    specs: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSONB)
    finalized: bool = Field(default=False)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
