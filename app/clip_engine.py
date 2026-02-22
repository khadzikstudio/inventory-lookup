import numpy as np
import torch
from PIL import Image
import open_clip

_model = None
_preprocess = None
_tokenizer = None
_device = None


def init_clip():
    global _model, _preprocess, _tokenizer, _device
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    _model, _, _preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k"
    )
    _tokenizer = open_clip.get_tokenizer("ViT-B-32")
    _model = _model.to(_device)
    _model.eval()


def encode_image(image_path):
    """Encode a single image file into a normalized embedding vector."""
    if _model is None:
        init_clip()
    img = Image.open(image_path).convert("RGB")
    img_tensor = _preprocess(img).unsqueeze(0).to(_device)
    with torch.no_grad():
        features = _model.encode_image(img_tensor)
    features = features / features.norm(dim=-1, keepdim=True)
    return features.cpu().numpy().flatten()


def encode_text(text):
    """Encode a text query into a normalized embedding vector."""
    if _model is None:
        init_clip()
    tokens = _tokenizer([text]).to(_device)
    with torch.no_grad():
        features = _model.encode_text(tokens)
    features = features / features.norm(dim=-1, keepdim=True)
    return features.cpu().numpy().flatten()


def cosine_similarity(vec_a, vec_b):
    return float(np.dot(vec_a, vec_b))
