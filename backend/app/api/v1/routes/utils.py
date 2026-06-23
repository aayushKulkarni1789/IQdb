from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from PIL import Image
import io

from app.core.clip import get_text_embedding, get_image_embedding

router = APIRouter(prefix="/utils", tags=["utils"])


class TextInput(BaseModel):
    text: str


@router.get("/health-check/")
def health_check() -> bool:
    return True


@router.post("/embed-text/")
def embed_text(body: TextInput):
    embedding = get_text_embedding(body.text)
    return {"embedding": embedding}


@router.post("/embed-image/")
async def embed_image(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    embedding = get_image_embedding(image)
    return {"embedding": embedding}
