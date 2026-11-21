"""Which kind of photo is this, and what crop is in the harvest?

People photograph the hosil as often as the growing plant, and the two need
different models:

  * PlantNet is trained on PlantCLEF - plants in the ground. On harvested
    produce it scored 0/7 in testing, answering "Lemna gibba" (duckweed) for
    a crate of grapes and "Salvinia molesta" (an aquatic fern) for a pile of
    potatoes.
  * CLIP compared against produce prompts scored 7/7 on those same photos,
    mostly at 1.00.

So the pipeline asks `classify_view` first and routes accordingly.
"""

from __future__ import annotations

import numpy as np
from PIL.Image import Image

from .gates import _image_vector, _scale, _softmax, _text_vectors
from .labels import (
    PRODUCE_OTHER,
    PRODUCE_PROMPTS,
    VIEW_HARVEST,
    VIEW_LEAF,
    VIEW_PLANT,
    VIEW_PROMPTS,
)

__all__ = [
    "PRODUCE_OTHER", "VIEW_HARVEST", "VIEW_LEAF", "VIEW_PLANT",
    "classify_view", "identify_produce",
]


def _pooled_scores(image: Image, groups: dict[str, list[str]]) -> list[tuple[str, float]]:
    """Softmax over groups of prompts, max-pooled within each group.

    Max-pooling means one good phrasing is enough, and a group is not
    rewarded merely for listing more alternatives.
    """
    texts: list[str] = []
    owners: list[str] = []
    for key, prompts in groups.items():
        for prompt in prompts:
            texts.append(f"a photo of {prompt}")
            owners.append(key)

    logits = _scale() * (_image_vector(image) @ _text_vectors(tuple(texts)).T)

    pooled: dict[str, float] = {}
    for owner, logit in zip(owners, logits):
        pooled[owner] = max(pooled.get(owner, -np.inf), float(logit))

    keys = list(pooled)
    probabilities = _softmax(np.array([pooled[k] for k in keys]))
    scored = list(zip(keys, (float(p) for p in probabilities)))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def classify_view(image: Image) -> tuple[str, float]:
    """Harvested produce, growing plant, or leaf close-up?

    Returns one of VIEW_HARVEST / VIEW_PLANT / VIEW_LEAF with its probability.
    """
    return _pooled_scores(image, VIEW_PROMPTS)[0]


def identify_produce(image: Image) -> list[tuple[str, float]]:
    """Which crop's harvest is this? (plants.json ids, best first)

    Only crops whose harvest a person would photograph are candidates, so an
    ornamental never gets forced into a produce answer. PRODUCE_OTHER may win,
    meaning "produce, but not one of ours".
    """
    return _pooled_scores(image, PRODUCE_PROMPTS)
