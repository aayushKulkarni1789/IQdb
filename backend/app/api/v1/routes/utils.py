from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from pydantic.json_schema import WithJsonSchema
from PIL import Image
from typing import List, Annotated
import io

from app.core.clip import get_text_embeddings, get_image_embeddings

router = APIRouter(prefix="/utils", tags=["utils"])


class TextInput(BaseModel):
    text: str


@router.get("/health-check/")
def health_check() -> bool:
    return True


@router.post("/embed-text/")
def embed_text(texts: List[str]):
    embeddings = get_text_embeddings(texts)
    return {"embeddings": embeddings}

Annotated[
        list[UploadFile],
        File(),
        WithJsonSchema(
            {
                "type": "array",
                "items": {
                    "type": "string",
                    "format": "binary",
                },
            }
        ),
    ]
@router.post("/embed-image/")
async def embed_image(
    files: Annotated[
        list[UploadFile],
        File(),
        WithJsonSchema(
            {
                "type": "array",
                "items": {
                    "type": "string",
                    "format": "binary",
                },
            }
        ),
    ]
):
    images = []
    for file in files:
        contents = await file.read()
        images.append(Image.open(io.BytesIO(contents)))
    embeddings = get_image_embeddings(images)
    return {"embeddings": embeddings}
