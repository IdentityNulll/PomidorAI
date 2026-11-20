"""Zero-shot crop identification with CLIP.

CLIP scores the photo against text prompts, so no training is needed: we ask
it which of the eight crops - or which of a set of "not a crop" distractors -
the image looks most like.
"""

from __future__ import annotations

from functools import lru_cache

from PIL.Image import Image

from .labels import (
    DISTRACTOR_PROMPTS,
    LEAF_PROMPTS,
    NOT_LEAF_PROMPTS,
    SPECIES_PROMPTS,
)
from .models import load

DISTRACTOR = "__not_a_crop__"


@lru_cache(maxsize=1)
def _prompt_index() -> tuple[list[str], list[str]]:
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

    return texts, owners


def identify(image: Image) -> list[tuple[str, float]]:
    """Score the image against every crop and the distractors.

    Returns (plant_id, probability) pairs sorted high to low, where plant_id
    may be DISTRACTOR. Probabilities sum to 1 across the returned entries.
    """
    bundle = load()
    torch = bundle.torch
    texts, owners = _prompt_index()

    inputs = bundle.clip_processor(
        text=texts, images=image, return_tensors="pt", padding=True
    )
    logits = bundle.clip(**inputs).logits_per_image[0]

    # Several prompts describe the same crop. Max-pool over a crop's prompts
    # before the softmax, so a crop is not rewarded for having more prompts.
    by_owner: dict[str, object] = {}
    for owner, logit in zip(owners, logits):
        current = by_owner.get(owner)
        if current is None or logit > current:
            by_owner[owner] = logit

    keys = list(by_owner)
    probabilities = torch.softmax(torch.stack([by_owner[k] for k in keys]), dim=0)

    scored = [(key, float(p)) for key, p in zip(keys, probabilities)]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def leafiness(image: Image) -> float:
    """How much the photo looks like the close-up leaf shots PlantVillage saw.

    Returns a probability in 0.0-1.0. Low values mean the disease model is
    being shown something outside its training distribution and its output
    should not be trusted.
    """
    bundle = load()
    torch = bundle.torch

    texts = [f"a photo of {p}" for p in LEAF_PROMPTS + NOT_LEAF_PROMPTS]
    inputs = bundle.clip_processor(
        text=texts, images=image, return_tensors="pt", padding=True
    )
    logits = bundle.clip(**inputs).logits_per_image[0]

    leaf = logits[: len(LEAF_PROMPTS)].max()
    other = logits[len(LEAF_PROMPTS) :].max()
    return float(torch.softmax(torch.stack([leaf, other]), dim=0)[0])
