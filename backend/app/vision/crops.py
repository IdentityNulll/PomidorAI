"""Recognising the 22 curated crops, from any angle, plus what view it is.

People photograph whatever is in front of them: the growing bush, a single
leaf, or the hosil in a crate. Two facts drove this design:

  * PlantNet is trained on PlantCLEF - wild flora rooted in the ground. On
    harvested produce it scored 0/7, answering "Lemna gibba" (duckweed) for
    a crate of grapes and "Salvinia molesta" for a heap of potatoes. It is
    also weak on cultivated vegetables, which PlantCLEF under-represents.

  * CLIP compared against prompts covering all three views of each crop
    scored 7/7 on that produce and 10/14 on a labelled set of real garden
    photos.

So this module gives every curated crop ONE class spanning plant, leaf and
harvest. The answer then does not depend on first guessing the view right -
which was the flaw in the previous attempt, where a pepper bush was read as
"hosil" and came back as quince.

`classify_view` is kept separately, but only to tell the user what the app
thinks it is looking at. It no longer routes anything.
"""

from __future__ import annotations

import numpy as np
from PIL.Image import Image

from .gates import _image_vector, _scale, _softmax, _text_vectors
from .prompts import CROP_OTHER, CROP_PROMPTS, VIEW_HARVEST, VIEW_LEAF, VIEW_PLANT, VIEW_PROMPTS

__all__ = [
    "CROP_OTHER", "VIEW_HARVEST", "VIEW_LEAF", "VIEW_PLANT",
    "classify_view", "identify_crop",
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


def identify_crop(image: Image) -> list[tuple[str, float]]:
    """Which curated crop is this? (plants.json ids, best first)

    CROP_OTHER may win, meaning "a plant, but not one of ours" - the caller
    should then fall back to the 7806-species model.
    """
    return _pooled_scores(image, CROP_PROMPTS)


def classify_view(image: Image) -> tuple[str, float]:
    """Harvested produce, growing plant, or leaf close-up?

    Shown to the user so they can see what the app read the photo as. It
    deliberately does not pick which model runs: an earlier version routed
    on this and a misread view produced confident wrong answers.
    """
    return _pooled_scores(image, VIEW_PROMPTS)[0]
