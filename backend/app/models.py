from datetime import datetime, timezone
from typing import Any

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import DateTime
from sqlmodel import Field, Index, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# --- Base (shared fields) ---


class ImageBase(SQLModel):
    filename: str
    uri: str = Field(unique=True)
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


# --- API response schemas ---


class ImagePublic(ImageBase):
    id: int
    created_at: datetime | None = None


class ImagesPublic(SQLModel):
    data: list[ImagePublic]
    count: int


# --- Database table ---


class Image(ImageBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )
    clip_embedding: "CLIPEmbedding | None" = Relationship(back_populates="image")


class CLIPEmbedding(SQLModel, table=True):
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
