from functools import lru_cache

try:
    import torch
    from transformers import CLIPModel, CLIPProcessor
except ImportError:  # pragma: no cover - host without torch still imports for tests
    torch = None  # type: ignore
    CLIPModel = None  # type: ignore
    CLIPProcessor = None  # type: ignore

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_clip():
    print(f"LOADING CLIP MODEL: {settings.CLIP_MODEL_NAME} from {settings.CLIP_MODEL_PATH}")
    model = CLIPModel.from_pretrained(settings.CLIP_MODEL_PATH)
    processor = CLIPProcessor.from_pretrained(settings.CLIP_MODEL_PATH)
    model.eval()
    return model, processor


# Note: the embedding generation logic might differ from what an AI agent might suggest,
# Because this is exclusive to transformers v5, which changed how clip inferencing works
# https://github.com/huggingface/transformers/blob/main/MIGRATION_GUIDE_V5.md#feature-extraction-helpers-get__features
def get_text_embeddings(texts: list[str]) -> list[list[float]]:
    if torch is None or CLIPModel is None:
        # Fallback for host env without torch (tests / local dev without model-setup).
        # Return deterministic unit vectors so rank tests and ingestion can proceed.
        return [[1.0 if j == 0 else 0.0 for j in range(512)] for _ in texts]
    model, processor = _get_clip()
    inputs = processor(text=texts, return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = model.get_text_features(**inputs, return_dict=True)
    return outputs.pooler_output.tolist()


def get_image_embeddings(image: list) -> list[list[float]]:
    if torch is None or CLIPModel is None:
        return [[float(idx % 7) for _ in range(512)] for idx, _ in enumerate(image)]
    model, processor = _get_clip()
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model.get_image_features(**inputs, return_dict=True)
    return outputs.pooler_output.tolist()
