import torch
from transformers import CLIPModel, CLIPProcessor
from app.core.config import settings

def load_clip():
    model = CLIPModel.from_pretrained(settings.CLIP_MODEL_PATH)
    processor = CLIPProcessor.from_pretrained(settings.CLIP_MODEL_PATH)
    model.eval()
    return model, processor

clip_model, clip_processor = load_clip()

def get_text_embedding(text: str) -> list[float]:
    inputs = clip_processor(text=[text], return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = clip_model.get_text_features(**inputs, return_dict=True)
    return outputs.pooler_output[0].tolist()

def get_image_embedding(image) -> list[float]:
    inputs = clip_processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = clip_model.get_image_features(**inputs, return_dict=True)
    return outputs.pooler_output[0].tolist()
