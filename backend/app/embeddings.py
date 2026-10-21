"""Optional local CLIP backend. Install requirements-ai.txt and opt in explicitly."""
from functools import lru_cache
import cv2
import numpy as np
from PIL import Image
from .config import settings

class ClipEncoder:
    def __init__(self):
        from transformers import CLIPModel, CLIPProcessor
        self.processor=CLIPProcessor.from_pretrained(settings().clip_model)
        self.model=CLIPModel.from_pretrained(settings().clip_model, use_safetensors=True).eval()
        if self.model.config.projection_dim != 512: raise ValueError('pgvector schema requires a 512-dimensional CLIP projection')
    def encode_image(self,frame):
        import torch
        inputs=self.processor(images=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)),return_tensors='pt')
        with torch.no_grad(): vector=self.model.get_image_features(**inputs).numpy()[0]
        return (vector/np.linalg.norm(vector)).tolist()
@lru_cache
def get_encoder(): return ClipEncoder()
