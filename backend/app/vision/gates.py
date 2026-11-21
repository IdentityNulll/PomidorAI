"""The two yes/no questions CLIP answers for the pipeline.

Neither specialist model can abstain. PlantNet returns a species for a photo
of a car; the PlantVillage classifier returns a disease for a photo of a
flower. So before either is trusted, CLIP is asked:

  plantness(image) - is there a plant in frame at all?
  leafiness(image) - is this the close-up single leaf the disease model
                     was trained on?

This module used to also do species identification with a trained 8-class
head. PlantNet (7806 species) replaced that; the head, its training scripts
and its weights were removed in the same change. Recoverable from git history
if the approach is ever wanted back.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from PIL.Image import Image

from .labels import LEAF_PROMPTS, NOT_LEAF_PROMPTS, NOT_PLANT_PROMPTS, PLANT_PROMPTS
from .models import load


def _image_vector(image: Image) -> np.ndarray:
    """L2-normalised CLIP image embedding."""
    bundle = load()
    with bundle.torch.no_grad():
        features = bundle.clip.get_image_features(
            **bundle.clip_processor(images=image, return_tensors="pt")
        )
        features = features.pooler_output if hasattr(features, "pooler_output") else features
        features = features / features.norm(dim=-1, keepdim=True)
        return features[0].numpy()


@lru_cache(maxsize=8)
def _text_vectors(texts: tuple[str, ...]) -> np.ndarray:
    """L2-normalised CLIP text embeddings, cached.

    The prompt sets are fixed, so without this every scan would re-encode the
    same few dozen strings through the text tower for nothing.
    """
    bundle = load()
    with bundle.torch.no_grad():
        features = bundle.clip.get_text_features(
            **bundle.clip_processor(text=list(texts), return_tensors="pt", padding=True)
        )
        features = features.pooler_output if hasattr(features, "pooler_output") else features
        features = features / features.norm(dim=-1, keepdim=True)
        return features.numpy()


@lru_cache(maxsize=1)
def _scale() -> float:
    bundle = load()
    with bundle.torch.no_grad():
        return float(bundle.clip.logit_scale.exp())


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = np.exp(values - values.max())
    return shifted / shifted.sum()


def _split_score(image: Image, yes: list[str], no: list[str]) -> float:
    """P(yes) from max-pooled similarity over two competing prompt sets.

    Max-pooling rather than averaging, so one well-matching phrasing is
    enough and a set is not penalised for listing many alternatives.
    """
    texts = tuple(f"a photo of {p}" for p in yes + no)
    logits = _scale() * (_image_vector(image) @ _text_vectors(texts).T)
    best_yes = logits[: len(yes)].max()
    best_no = logits[len(yes) :].max()
    return float(_softmax(np.array([best_yes, best_no]))[0])


def plantness(image: Image) -> list[tuple[str, float]]:
    """Is there a plant in this photo at all?

    Returns [("plant", p), ("not_plant", 1 - p)].
    """
    probability = _split_score(image, PLANT_PROMPTS, NOT_PLANT_PROMPTS)
    return [("plant", probability), ("not_plant", 1.0 - probability)]


def leafiness(image: Image) -> float:
    """How much the photo looks like the close-up leaf shots PlantVillage saw.

    Low values mean the disease model is being shown something outside its
    training distribution and its output should not be trusted.
    """
    return _split_score(image, LEAF_PROMPTS, NOT_LEAF_PROMPTS)
