"""Crop identification from CLIP image features.

Two paths, in order of preference:

1. A trained linear head over frozen CLIP features (weights/species_head.npz).
   Fitted on real photographs of these eight crops, including deliberately
   downscaled and re-compressed copies, so it holds up on low-resolution phone
   uploads. Train it with backend/scripts/train_head.py.

2. Zero-shot text prompts, used when no trained head is present so the app
   still works on a fresh checkout. Noticeably weaker.

Both emit the same (class, probability) ranking, where the class may be
DISTRACTOR for "not one of our crops".
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL.Image import Image

from .labels import (
    DISTRACTOR_PROMPTS,
    LEAF_PROMPTS,
    NOT_LEAF_PROMPTS,
    SPECIES_PROMPTS,
)
from .models import load

DISTRACTOR = "__not_a_crop__"
HEAD_FILE = Path(__file__).parent / "weights" / "species_head.npz"


@lru_cache(maxsize=1)
def _prompt_index() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Flatten prompts into one list, plus the owning key for each prompt."""
    texts: list[str] = []
    owners: list[str] = []

    for plant_id, prompts in SPECIES_PROMPTS.items():
        for prompt in prompts:
            texts.append(f"a photo of {prompt}")
            owners.append(plant_id)

    for prompt in DISTRACTOR_PROMPTS:
        texts.append(f"a photo of {prompt}")
        owners.append(DISTRACTOR)

    return tuple(texts), tuple(owners)


@lru_cache(maxsize=1)
def _head():
    """The trained linear head, or None if this checkout has no weights."""
    if not HEAD_FILE.exists():
        return None
    blob = np.load(HEAD_FILE, allow_pickle=True)
    return blob["weights"], blob["bias"], [str(x) for x in blob["labels"]]


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


def _prompt_logits(image: Image, texts: tuple[str, ...]) -> np.ndarray:
    """CLIP similarity logits between one image and a fixed prompt set."""
    bundle = load()
    scale = float(bundle.clip.logit_scale.exp())
    return scale * (_image_vector(image) @ _text_vectors(texts).T)


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = np.exp(values - values.max())
    return shifted / shifted.sum()


# Geometric blend of the trained head and the zero-shot prompts. The two make
# different mistakes - the head can read an unusual whole-plant shot as "not a
# crop", the prompts are weak on fine-grained leaves - and combining them beats
# either alone. Chosen on one half of the held-out split and confirmed on the
# other: 0.793 blended vs 0.779 head-only vs 0.657 zero-shot.
BLEND_ALPHA = 0.75


def identify(image: Image) -> list[tuple[str, float]]:
    """Score the image against every crop and the distractors.

    Returns (plant_id, probability) pairs sorted high to low, where plant_id
    may be DISTRACTOR. Probabilities sum to 1 across the returned entries.
    """
    head = _head()
    if head is None:
        return identify_zero_shot(image)

    weights, bias, labels = head
    vector = _image_vector(image)
    head_probabilities = _softmax(vector @ weights + bias)

    zero_shot = dict(identify_zero_shot(image))
    prompt_probabilities = np.array(
        [zero_shot.get(label, 1e-9) for label in labels], dtype=np.float64
    )

    blended = head_probabilities**BLEND_ALPHA * prompt_probabilities ** (1 - BLEND_ALPHA)
    blended /= blended.sum()

    scored = [(label, float(p)) for label, p in zip(labels, blended)]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def identify_zero_shot(image: Image) -> list[tuple[str, float]]:
    """Prompt-based identification; the fallback when no head is trained."""
    texts, owners = _prompt_index()
    logits = _prompt_logits(image, texts)

    # Several prompts describe the same crop. Max-pool over a crop's prompts
    # before the softmax, so a crop is not rewarded for having more prompts.
    by_owner: dict[str, float] = {}
    for owner, logit in zip(owners, logits):
        by_owner[owner] = max(by_owner.get(owner, -np.inf), float(logit))

    keys = list(by_owner)
    probabilities = _softmax(np.array([by_owner[k] for k in keys]))

    scored = [(key, float(p)) for key, p in zip(keys, probabilities)]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def leafiness(image: Image) -> float:
    """How much the photo looks like the close-up leaf shots PlantVillage saw.

    Returns a probability in 0.0-1.0. Low values mean the disease model is
    being shown something outside its training distribution and its output
    should not be trusted.
    """
    texts = tuple(f"a photo of {p}" for p in LEAF_PROMPTS + NOT_LEAF_PROMPTS)
    logits = _prompt_logits(image, texts)

    leaf = logits[: len(LEAF_PROMPTS)].max()
    other = logits[len(LEAF_PROMPTS) :].max()
    return float(_softmax(np.array([leaf, other]))[0])
