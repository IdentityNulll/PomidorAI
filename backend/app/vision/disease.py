"""Health assessment, and the crop evidence the leaf model provides.

Two paths, because no single local model covers all eight crops:

1. tomato / potato / apple / grape -> a real PlantVillage-trained classifier.
   It is accurate on close-up leaf photos resembling its training data (one
   leaf, plain background) and unreliable on anything else, so callers gate it
   on species.leafiness().

2. cotton / wheat / pomegranate / apricot -> CLIP scoring "healthy" against
   "diseased" prompts. A genuinely weak signal, reported with capped
   confidence so the UI shows its unsure state.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from PIL.Image import Image

from .labels import CROP_BY_PLANT_ID, DISEASE_UZ, HEALTH_PROMPTS, HEALTHY, SPECIES_PROMPTS
from .models import load
from .thresholds import UNSURE_CAP

PLANT_ID_BY_CROP = {crop: plant_id for plant_id, crop in CROP_BY_PLANT_ID.items()}

# The CLIP fallback distinguishes rough state, not specific diseases, so its
# confidence stays below the UI's "sure" threshold.
FALLBACK_CONFIDENCE_CAP = UNSURE_CAP


@dataclass
class LeafReading:
    """One pass of the disease model over a leaf photo."""

    probabilities: object  # torch tensor over the model's 38 classes
    crop_mass: dict[str, float]  # crop prefix -> summed probability

    def best_crop(self) -> tuple[str | None, float]:
        """Most likely crop as one of our plants.json ids, with its mass."""
        for crop, mass in sorted(self.crop_mass.items(), key=lambda i: -i[1]):
            plant_id = PLANT_ID_BY_CROP.get(crop)
            if plant_id:
                return plant_id, mass
        return None, 0.0


def read_leaf(image: Image) -> LeafReading:
    """Run the disease model once and summarise it per crop."""
    bundle = load()
    torch = bundle.torch

    with torch.no_grad():
        logits = bundle.disease(
            **bundle.disease_processor(images=image, return_tensors="pt")
        ).logits[0]
    probabilities = torch.softmax(logits, dim=0)

    mass: dict[str, float] = defaultdict(float)
    for index, label in bundle.disease_labels.items():
        mass[label.split("___")[0]] += float(probabilities[index])

    return LeafReading(probabilities=probabilities, crop_mass=dict(mass))


def from_reading(reading: LeafReading, plant_id: str) -> list[dict]:
    """Top-3 Uzbek predictions for a crop the disease model covers."""
    bundle = load()
    torch = bundle.torch
    crop = CROP_BY_PLANT_ID[plant_id]

    indices = [i for i, label in bundle.disease_labels.items() if label.startswith(f"{crop}___")]
    if not indices:  # pragma: no cover - guarded by CROP_BY_PLANT_ID
        return []

    # Renormalise within the crop: the species is already decided, so another
    # crop's diseases would only add noise.
    subset = torch.stack([reading.probabilities[i] for i in indices])
    renormalised = subset / subset.sum()

    scored: dict[str, float] = {}
    for index, probability in zip(indices, renormalised):
        uz = DISEASE_UZ.get(bundle.disease_labels[index], _humanise(bundle.disease_labels[index]))
        # Several raw labels can share an Uzbek name; keep the strongest.
        scored[uz] = max(scored.get(uz, 0.0), float(probability))

    ranked = sorted(scored.items(), key=lambda item: item[1], reverse=True)[:3]
    return [{"label": label, "confidence": round(value, 2)} for label, value in ranked]


def clip_fallback(image: Image, plant_id: str, scientific: str = "") -> list[dict]:
    """Rough healthy-vs-diseased for crops the disease model does not cover.

    Prompts are built from the plant's own name. Not every curated crop has a
    hand-written CLIP prompt (and the species model knows 7806 plants that
    never will), so fall back to the scientific name, then to a generic
    "plant" - never assume a prompt exists.
    """
    bundle = load()
    torch = bundle.torch

    prompts = SPECIES_PROMPTS.get(plant_id)
    if prompts:
        plant = prompts[0].removeprefix("a ").removeprefix("an ")
    else:
        plant = scientific or "plant"

    texts: list[str] = []
    owners: list[str] = []
    for label, templates in HEALTH_PROMPTS.items():
        for template in templates:
            texts.append(f"a photo of {template.format(plant=plant)}")
            owners.append(label)

    inputs = bundle.clip_processor(text=texts, images=image, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = bundle.clip(**inputs).logits_per_image[0]

    pooled: dict[str, object] = {}
    for owner, logit in zip(owners, logits):
        current = pooled.get(owner)
        if current is None or logit > current:
            pooled[owner] = logit

    keys = list(pooled)
    probabilities = torch.softmax(torch.stack([pooled[k] for k in keys]), dim=0)

    ranked = sorted(
        ((key, float(p)) for key, p in zip(keys, probabilities)),
        key=lambda item: item[1],
        reverse=True,
    )
    return [
        {"label": label, "confidence": round(min(value, FALLBACK_CONFIDENCE_CAP), 2)}
        for label, value in ranked
    ]


def unsure(predictions: list[dict]) -> list[dict]:
    """Keep the ranking but cap confidence into the UI's unsure band."""
    return [
        {"label": p["label"], "confidence": round(min(p["confidence"], FALLBACK_CONFIDENCE_CAP), 2)}
        for p in predictions
    ]


def _humanise(raw_label: str) -> str:
    """Last-resort readable form if a label is missing from DISEASE_UZ."""
    name = raw_label.split("___", 1)[-1]
    return HEALTHY if name.lower() == "healthy" else name.replace("_", " ")
