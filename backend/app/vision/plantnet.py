"""Species identification across 7806 plants (PlantNet / PlantCLEF 2024).

This replaces the eight-class linear probe that used to do species ID. That
head could only ever answer with one of eight crops, so a pepper plant, a
coriander patch or an autumn quince tree came back as a confident wrong crop.

The model is `PlantNet/mobilenetv4-conv-s-plantclef2024` (Apache-2.0), trained
on PlantCLEF 2024. It is small and fast on CPU - around 40-90 ms per image,
quicker than the CLIP pass it replaces.

Its own labels are numeric PlantNet species ids; the scientific names come
from the companion `species_id_to_name.txt` published with the PlantNet ViT
checkpoint. Both are cached locally after the first download.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL.Image import Image

logger = logging.getLogger(__name__)

MODEL = os.environ.get("POMIDORAI_SPECIES_MODEL", "PlantNet/mobilenetv4-conv-s-plantclef2024")
# Only published with the ViT checkpoint, but it maps the same id space.
NAMES_REPO = os.environ.get(
    "POMIDORAI_SPECIES_NAMES", "PlantNet/vit_base_patch14_reg4_dinov2_lvd142m.pc24_all"
)
NAMES_FILE = "species_id_to_name.txt"

_lock = threading.Lock()
_bundle: Species | None = None


@dataclass
class Species:
    model: Any
    transform: Any
    torch: Any
    labels: list[str]  # index -> PlantNet species id
    names: dict[str, str]  # species id -> scientific name


def load() -> Species:
    """Load the species model, once, on first use."""
    global _bundle
    if _bundle is not None:
        return _bundle

    with _lock:
        if _bundle is not None:
            return _bundle

        try:
            import timm
            import torch
            from huggingface_hub import hf_hub_download, snapshot_download
        except ImportError as exc:  # pragma: no cover - environment problem
            raise RuntimeError(
                "Species model dependencies missing. Install with: "
                "pip install -r backend/requirements.txt"
            ) from exc

        logger.info("loading species model: %s", MODEL)
        model = timm.create_model(f"hf_hub:{MODEL}", pretrained=True).eval()
        config = timm.data.resolve_model_data_config(model)
        transform = timm.data.create_transform(**config, is_training=False)

        snapshot = Path(snapshot_download(MODEL, allow_patterns=["config.json"]))
        labels = json.loads((snapshot / "config.json").read_text())["label_names"]

        names: dict[str, str] = {}
        path = hf_hub_download(NAMES_REPO, NAMES_FILE)
        with open(path, encoding="utf-8") as handle:
            for row in csv.DictReader(handle, delimiter=";", quotechar='"'):
                names[row["species_id"]] = row["species"]

        _bundle = Species(model, transform, torch, labels, names)
        logger.info("species model ready (%d classes)", len(labels))
        return _bundle


@lru_cache(maxsize=1)
def species_list() -> list[str]:
    """Every scientific name the model can emit, cleaned of author strings.

    PlantCLEF names carry botanical authorities ("Taxus baccata L."), which
    Wikidata's taxon names do not, so strip to genus + epithet.
    """
    bundle = load()
    out = {clean_name(n) for n in bundle.names.values()}
    return sorted(out)


def clean_name(scientific: str) -> str:
    """'Cydonia oblonga Mill.' -> 'Cydonia oblonga'."""
    parts = scientific.replace("× ", "").split()
    if len(parts) >= 2 and parts[1][:1].islower():
        return f"{parts[0]} {parts[1]}"
    return parts[0] if parts else scientific


def identify(image: Image, top: int = 5) -> list[tuple[str, float]]:
    """Top species for an image as (scientific name, probability)."""
    bundle = load()
    torch = bundle.torch

    with torch.no_grad():
        tensor = bundle.transform(image).unsqueeze(0)
        probabilities = bundle.model(tensor).softmax(-1)[0]

    best = torch.topk(probabilities, top)
    out: list[tuple[str, float]] = []
    for value, index in zip(best.values, best.indices):
        species_id = bundle.labels[int(index)]
        out.append((clean_name(bundle.names.get(species_id, species_id)), float(value)))
    return out


def warm() -> None:
    """Preload at startup; never fatal."""
    try:
        load()
    except Exception:  # pragma: no cover
        logger.exception("could not preload species model")
