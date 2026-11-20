"""The single analysis seam.

Everything the app knows about plant identification and disease detection
comes from analyze(). The models live in the vision/ package; this module is
the only thing main.py calls.

Both models run locally on CPU. Nothing is sent anywhere.

Routing, which matters because each model is only good in its own domain:

  * Whole-plant, fruit or field photos -> CLIP zero-shot over the eight crops,
    plus "not a crop" distractors so a photo of a cat comes back unidentified
    instead of being forced into the nearest crop. CLIP is strong here.

  * Close-up leaf photos -> the PlantVillage-trained classifier decides the
    crop, because that is exactly what it was trained on and CLIP is weak at
    fine-grained leaf shapes (it reads most broad green leaves as cotton).
    When neither model is confident we report unsure rather than guessing.

Known limitation: tomato and potato late blight are the same pathogen on
similar leaves, and a potato leaf is sometimes reported as tomato. The disease
answer stays correct in that case.

NOTE: the reference content in data/plants.json and the Uzbek disease names in
vision/labels.py are machine-written and still need agronomist review.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PIL import Image

from .vision import disease as disease_model
from .vision import species as species_model

logger = logging.getLogger(__name__)

PLANTS_FILE = Path(__file__).parent / "data" / "plants.json"

# The UI hides the name and asks for a clearer photo below this.
UNSURE_BELOW = 0.50
UNSURE_CAP = 0.49

# Above this the photo is close-up-leaf-like enough to trust the leaf model.
LEAF_REQUIRED = 0.55
# The leaf model must be at least this sure of the crop to override CLIP.
CROP_MASS_REQUIRED = 0.50

with PLANTS_FILE.open(encoding="utf-8") as handle:
    _PLANTS = {plant["id"]: plant for plant in json.load(handle)}


def analyze(image_path: str) -> dict:
    """Identify the plant in an image and assess its health.

    Args:
        image_path: absolute path to a normalised JPEG on local disk.

    Returns:
        {
          "plant":  {"id", "commonName", "scientificName", "confidence"},
          "health": {"predictions": [{"label", "confidence"}, ...]},
          "info":   {"description", "howItGrows", "water", "sunlight", "soil",
                     "season", "commonDiseases": [...], "careTips": [...]},
        }
        Confidences are calibrated probabilities in 0.0-1.0.
    """
    with Image.open(image_path) as handle:
        image = handle.convert("RGB")

    clip_ranked = species_model.identify(image)
    clip_id, clip_score = clip_ranked[0]
    leafy = species_model.leafiness(image)

    is_leaf = leafy >= LEAF_REQUIRED
    if is_leaf:
        plant_id, confidence, reading = _identify_leaf(image, clip_id, clip_score)
    else:
        plant_id, confidence, reading = clip_id, clip_score, None

    if plant_id == species_model.DISTRACTOR:
        logger.info("no crop recognised (leafy=%.2f)", leafy)
        return _unidentified(confidence)

    plant = _PLANTS[plant_id]
    predictions = _assess(image, plant_id, confidence, reading, is_leaf)

    logger.info("identified %s at %.2f (leafy=%.2f)", plant_id, confidence, leafy)
    return {
        "plant": {
            "id": plant["id"],
            "commonName": plant["commonName"],
            "scientificName": plant["scientificName"],
            "confidence": round(confidence, 2),
        },
        "health": {"predictions": predictions},
        "info": {
            "description": plant["description"],
            "howItGrows": plant["howItGrows"],
            "water": plant["water"],
            "sunlight": plant["sunlight"],
            "soil": plant["soil"],
            "season": plant["season"],
            "commonDiseases": plant["commonDiseases"],
            "careTips": plant["careTips"],
        },
    }


def _identify_leaf(image, clip_id: str, clip_score: float):
    """Decide the crop for a close-up leaf, preferring the leaf model."""
    reading = disease_model.read_leaf(image)
    leaf_id, mass = reading.best_crop()

    if leaf_id and mass >= CROP_MASS_REQUIRED:
        return leaf_id, mass, reading

    # Neither model is convincing on this leaf. CLIP's answer here is not
    # trustworthy, so pass it through but capped into the unsure band.
    return clip_id, min(clip_score, UNSURE_CAP), reading


def _assess(image, plant_id: str, confidence: float, reading, is_leaf: bool) -> list[dict]:
    """Health predictions, never more certain than the species they assume."""
    covered = plant_id in disease_model.CROP_BY_PLANT_ID

    if covered:
        predictions = disease_model.from_reading(
            reading if reading is not None else disease_model.read_leaf(image), plant_id
        )
    else:
        predictions = disease_model.clip_fallback(image, plant_id)

    # Two reasons to withhold certainty: the photo is not the close-up leaf
    # the disease model expects, or the species underneath is itself a guess.
    if (covered and not is_leaf) or confidence < UNSURE_BELOW:
        return disease_model.unsure(predictions)
    return predictions


def _unidentified(score: float) -> dict:
    """Result for a photo that is not one of the eight crops.

    The shape stays identical; confidences sit under UNSURE_BELOW so the UI
    shows "Ishonchim komil emas" for both the plant and the health section.
    """
    confidence = round(min(score, UNSURE_CAP), 2)
    return {
        "plant": {
            "id": "unknown",
            "commonName": "",
            "scientificName": "",
            "confidence": confidence,
        },
        "health": {"predictions": [{"label": "Sog'lom", "confidence": confidence}]},
        "info": {
            "description": "",
            "howItGrows": "",
            "water": "",
            "sunlight": "",
            "soil": "",
            "season": "",
            "commonDiseases": [],
            "careTips": [],
        },
    }
