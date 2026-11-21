"""Learning from user corrections, without a training run.

When someone tells the app "that is not quince, it is peach", the CLIP
embedding of their photo is stored with the right label. Every later photo
is compared against that memory first, and a close enough match wins.

Why nearest-neighbour rather than training a head:

  * It works from the very first correction. A linear head needs tens of
    examples per class before it beats the prompts.
  * It takes effect immediately - no retraining step, no redeploy.
  * It cannot damage the crops that already work, because it only fires
    above a similarity threshold.

Once enough corrections accumulate, scripts/train_corrections.py fits a
proper head over the same vectors; this stays as the fast path for the
long tail.
"""

from __future__ import annotations

import logging

import numpy as np
from PIL.Image import Image

from .gates import _image_vector

logger = logging.getLogger(__name__)

# Cosine similarity above which a remembered photo is considered the same
# plant. Measured, after 0.80 turned out to leak badly: correcting two peach
# photos relabelled five quince photos of the same autumn garden, at up to
# 0.95 confidence. Across 20 labelled photos and 4 corrections:
#
#   same plant      min 0.999
#   different plant max 0.901   <- quince photos matching a peach correction
#
# 0.92 recalled every genuine match and leaked none. Corrections are biased
# hard towards precision: one that fails to fire is a missed improvement,
# one that leaks spreads a confident wrong answer - the very thing this
# feature exists to fix.
MATCH_THRESHOLD = 0.92

# The best match must also beat the best match carrying a DIFFERENT label by
# this much, so a near-tie between two crops never fires.
MATCH_MARGIN = 0.02

# A correction is evidence, not proof - cap what it can claim so a single
# mislabelled photo cannot produce a 1.00.
MAX_CONFIDENCE = 0.95


def encode(image: Image) -> bytes:
    """CLIP embedding of an image, as bytes for the database."""
    return _image_vector(image).astype(np.float32).tobytes()


def decode(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def recall(image: Image, corrections: list[tuple[str, bytes]]) -> tuple[str, float] | None:
    """Closest remembered correction for this photo, if any is close enough.

    Args:
        image: the photo being analysed.
        corrections: (plant_id, embedding bytes) rows from the database.

    Returns:
        (plant_id, confidence) or None when nothing is similar enough.
    """
    if not corrections:
        return None

    vector = _image_vector(image)
    matrix = np.stack([decode(blob) for _, blob in corrections])
    # Both sides are already L2-normalised, so a dot product is the cosine.
    similarities = matrix @ vector

    best = int(similarities.argmax())
    score = float(similarities[best])
    if score < MATCH_THRESHOLD:
        return None

    plant_id = corrections[best][0]

    # A near-tie between two different crops is not evidence of either.
    rival = max(
        (float(value) for index, value in enumerate(similarities)
         if corrections[index][0] != plant_id),
        default=0.0,
    )
    if score - rival < MATCH_MARGIN:
        logger.info("correction for %s too close to a rival label, ignoring", plant_id)
        return None

    # Agreement among several neighbours is stronger evidence than one.
    close = similarities >= MATCH_THRESHOLD
    agreeing = sum(
        1 for index, hit in enumerate(close) if hit and corrections[index][0] == plant_id
    )
    confidence = min(MAX_CONFIDENCE, score + 0.05 * (agreeing - 1))

    logger.info("recalled %s from %d correction(s), similarity %.2f",
                plant_id, agreeing, score)
    return plant_id, confidence
