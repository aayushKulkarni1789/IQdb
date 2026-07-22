from functools import lru_cache

import torch
from transformers import CLIPModel, CLIPProcessor

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_clip():
    print(f"LOADING CLIP MODEL: {settings.CLIP_MODEL_NAME} from {settings.CLIP_MODEL_PATH}")
    model = CLIPModel.from_pretrained(settings.CLIP_MODEL_PATH)
    processor = CLIPProcessor.from_pretrained(settings.CLIP_MODEL_PATH)
    model.eval()
    return model, processor


def get_text_embeddings(texts: list[str]) -> list[list[float]]:
    model, processor = _get_clip()
    inputs = processor(text=texts, return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = model.get_text_features(**inputs, return_dict=True)
    return outputs.pooler_output.tolist()


def get_image_embeddings(image: list) -> list[list[float]]:
    model, processor = _get_clip()
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model.get_image_features(**inputs, return_dict=True)
    return outputs.pooler_output.tolist()
