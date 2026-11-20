"""The single analysis seam.

Everything the app knows about plant identification and disease detection comes
from analyze(). Today it returns mock data; swapping in the real models means
editing only this file, as long as the returned shape stays the same.

NOTE: the plant content served from data/plants.json is machine-written
placeholder text and must be verified by an agronomist - see data/README.md.
"""

import json
import random
import time
from pathlib import Path

PLANTS_FILE = Path(__file__).parent / "data" / "plants.json"

HEALTHY_LABEL = "Sog'lom"
MOCK_DELAY_SECONDS = 1.2
LOW_CONFIDENCE_RATE = 0.2

with PLANTS_FILE.open(encoding="utf-8") as handle:
    _PLANTS = json.load(handle)


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
        Confidences are floats in 0.0-1.0. The UI treats anything below 0.50 as
        "not sure" and hides the name, so a real model must return calibrated
        probabilities rather than raw logits.
    """
    del image_path  # the mock does not look at the pixels

    time.sleep(MOCK_DELAY_SECONDS)

    plant = random.choice(_PLANTS)

    return {
        "plant": {
            "id": plant["id"],
            "commonName": plant["commonName"],
            "scientificName": plant["scientificName"],
            "confidence": _mock_confidence(),
        },
        "health": {"predictions": _mock_health(plant["commonDiseases"])},
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


def _mock_confidence() -> float:
    """Occasionally return a low value so the UI's unsure state gets exercised."""
    if random.random() < LOW_CONFIDENCE_RATE:
        return round(random.uniform(0.18, 0.49), 2)
    return round(random.uniform(0.72, 0.98), 2)


def _mock_health(diseases: list[str]) -> list[dict]:
    """Build three health predictions that always include the healthy label."""
    labels = [HEALTHY_LABEL] + random.sample(diseases, min(2, len(diseases)))

    weights = sorted(
        (random.uniform(0.05, 1.0) for _ in labels), reverse=random.random() > 0.5
    )
    total = sum(weights)
    predictions = [
        {"label": label, "confidence": round(weight / total, 2)}
        for label, weight in zip(labels, weights)
    ]
    predictions.sort(key=lambda item: item["confidence"], reverse=True)
    return predictions[:3]
