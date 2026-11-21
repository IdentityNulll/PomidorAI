"""The single analysis seam.

Everything the app knows about plants comes from analyze(). The models live
in the vision/ package; this module is the only thing main.py calls. All of
it runs locally on CPU - nothing is sent anywhere.

Three models, each doing only what it is good at:

  * PlantNet (PlantCLEF 2024, 7806 species) decides WHAT the plant is. It
    replaced an eight-crop classifier that could only ever answer with one of
    eight crops, so a pepper plant or a coriander patch came back as a
    confident wrong crop.

  * CLIP answers two yes/no questions the species model cannot: "is this a
    plant at all?" (otherwise a photo of a car returns a confident species)
    and "is this a close-up leaf?" (which gates the disease model).

  * A PlantVillage classifier reads disease, but only for the 14 crops it was
    trained on and only on close-up leaves. Everywhere else the health result
    is deliberately capped into the UI's "not sure" band.

Information shown about a plant comes in three tiers - a curated Uzbek
agronomy card, a Wikidata Uzbek name, or the bare scientific name. See
vision/names.py; we do not invent growing advice for species we have not
checked.

NOTE: the Uzbek content in data/plants.json and the disease names in
vision/labels.py are machine-written and still need agronomist review.
"""

from __future__ import annotations

import logging

from PIL import Image

from .vision import disease as disease_model
from .vision import names
from .vision import plantnet
from .vision import thresholds
from .vision import gates as clip_gate

logger = logging.getLogger(__name__)

# Shared with disease.py; see vision/thresholds.py for how 0.30 was measured.
UNSURE_BELOW = thresholds.UNSURE_BELOW
UNSURE_CAP = thresholds.UNSURE_CAP

# Above this the photo is close-up-leaf-like enough to trust the leaf model.
LEAF_REQUIRED = 0.55
# The leaf model must be at least this sure of the crop to override PlantNet.
CROP_MASS_REQUIRED = 0.60
# ...and PlantNet must be below this, or its answer stands. The species model
# knows 7806 plants; the leaf model knows 14 and cannot abstain.
PLANTNET_TRUSTED = 0.35
# Below this the photo probably is not a plant at all.
PLANT_REQUIRED = 0.35

EMPTY_INFO = {
    "description": "", "howItGrows": "", "water": "", "sunlight": "",
    "soil": "", "season": "", "commonDiseases": [], "careTips": [],
}


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

    if not _looks_like_a_plant(image):
        logger.info("not a plant")
        return _unidentified()

    ranked = plantnet.identify(image)
    scientific, confidence = ranked[0]
    leafy = clip_gate.leafiness(image)
    is_leaf = leafy >= LEAF_REQUIRED

    reading = None
    if is_leaf:
        reading = disease_model.read_leaf(image)
        scientific, confidence = _refine_with_leaf(reading, scientific, confidence)

    plant_id, common, info = _resolve(scientific)
    predictions = _assess(image, plant_id, confidence, reading, is_leaf, scientific)

    logger.info("identified %s (%.2f) leafy=%.2f", scientific, confidence, leafy)
    return {
        "plant": {
            "id": plant_id,
            "commonName": common,
            "scientificName": scientific,
            "confidence": round(min(confidence, 1.0), 2),
        },
        "health": {"predictions": predictions},
        "info": info,
    }


def _looks_like_a_plant(image) -> bool:
    """CLIP gate. PlantNet always returns a species, even for a pizza."""
    ranked = dict(clip_gate.plantness(image))
    return ranked.get("plant", 0.0) >= PLANT_REQUIRED


def _refine_with_leaf(reading, scientific: str, confidence: float):
    """On a close-up leaf, let the leaf model have a say about the species.

    Only a say, never the last word when PlantNet is sure. The leaf model has
    14 classes and no way to answer "none of mine", so on a beet leaf it
    confidently says Tomato. Letting that override a correct PlantNet call
    turned a correct "Lavlagi 0.86" into "Pomidor 0.69" on one of the test
    photos. So it may only speak up when PlantNet is itself unsure.
    """
    leaf_id, mass = reading.best_crop()
    curated = names.by_plant_id(leaf_id) if leaf_id else None
    if not curated or mass < CROP_MASS_REQUIRED:
        return scientific, confidence

    if curated["scientificName"] == scientific:
        # Two independent models agreeing is the one case worth boosting.
        return scientific, max(confidence, mass)

    if confidence >= PLANTNET_TRUSTED:
        return scientific, confidence

    return curated["scientificName"], min(mass, UNSURE_CAP + 0.2)


def _resolve(scientific: str) -> tuple[str, str, dict]:
    """(plant_id, Uzbek display name, info card) for a scientific name."""
    curated = names.curated(scientific)
    if curated:
        return curated["id"], curated["commonName"], {
            key: curated[key] for key in EMPTY_INFO
        }

    uz = names.uzbek_name(scientific)
    info = dict(EMPTY_INFO)
    described = names.describe(scientific)
    if described:
        info["description"] = described
    return "wild", uz or "", info


def _assess(image, plant_id: str, confidence: float, reading, is_leaf: bool,
            scientific: str = "") -> list[dict]:
    """Health predictions, never more certain than the species they assume."""
    covered = plant_id in disease_model.CROP_BY_PLANT_ID

    if covered:
        predictions = disease_model.from_reading(
            reading if reading is not None else disease_model.read_leaf(image), plant_id
        )
    elif plant_id != "wild":
        predictions = disease_model.clip_fallback(image, plant_id, scientific)
    else:
        # No disease model and no prompts we trust for an arbitrary species.
        predictions = [{"label": disease_model.HEALTHY, "confidence": UNSURE_CAP}]

    if (covered and not is_leaf) or confidence < UNSURE_BELOW or plant_id == "wild":
        return disease_model.unsure(predictions)
    return predictions


def _unidentified() -> dict:
    """Result for a photo that is not a plant.

    Shape stays identical; confidences sit under UNSURE_BELOW so the UI shows
    "Ishonchim komil emas" for both the plant and the health section.
    """
    return {
        "plant": {"id": "unknown", "commonName": "", "scientificName": "", "confidence": 0.0},
        "health": {"predictions": [{"label": disease_model.HEALTHY, "confidence": 0.0}]},
        "info": dict(EMPTY_INFO),
    }
