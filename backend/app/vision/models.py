"""Lazy, cached loading of the local vision models.

Both models are downloaded once into the Hugging Face cache and then run
entirely offline on CPU. Loading is deferred to the first call so importing
the app (in tests, or just to read the API schema) stays fast.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

CLIP_MODEL = os.environ.get("POMIDORAI_CLIP_MODEL", "laion/CLIP-ViT-B-32-laion2B-s34B-b79K")
DISEASE_MODEL = os.environ.get(
    "POMIDORAI_DISEASE_MODEL", "kimcomehome/plantvillage-vit-leaf-disease"
)

_lock = threading.Lock()
_bundle: Bundle | None = None


@dataclass
class Bundle:
    torch: Any
    clip: Any
    clip_processor: Any
    disease: Any
    disease_processor: Any
    disease_labels: dict[int, str]


def load() -> Bundle:
    """Return the loaded models, loading them on first use.

    Raises RuntimeError if the dependencies or weights are unavailable, which
    the analyzer turns into a clear error rather than a wrong answer.
    """
    global _bundle
    if _bundle is not None:
        return _bundle

    with _lock:
        if _bundle is not None:
            return _bundle

        try:
            import torch
            from transformers import (
                AutoImageProcessor,
                AutoModelForImageClassification,
                CLIPModel,
                CLIPProcessor,
            )
        except ImportError as exc:  # pragma: no cover - environment problem
            raise RuntimeError(
                "Vision dependencies are missing. Install them with: "
                "pip install -r backend/requirements.txt"
            ) from exc

        # NB: torch.set_grad_enabled is thread-local, so setting it here would
        # only cover the thread that happened to load the models - requests
        # served from other threadpool threads would still build a graph and
        # then fail on .numpy(). Inference sites use torch.no_grad() instead.
        #
        # One thread per core is counterproductive for these small models and
        # makes latency worse under concurrent requests.
        torch.set_num_threads(max(1, (os.cpu_count() or 4) // 2))

        logger.info("loading CLIP: %s", CLIP_MODEL)
        clip = CLIPModel.from_pretrained(CLIP_MODEL).eval()
        clip_processor = CLIPProcessor.from_pretrained(CLIP_MODEL)

        logger.info("loading disease model: %s", DISEASE_MODEL)
        disease = AutoModelForImageClassification.from_pretrained(DISEASE_MODEL).eval()
        disease_processor = AutoImageProcessor.from_pretrained(DISEASE_MODEL)

        _bundle = Bundle(
            torch=torch,
            clip=clip,
            clip_processor=clip_processor,
            disease=disease,
            disease_processor=disease_processor,
            disease_labels={int(k): v for k, v in disease.config.id2label.items()},
        )
        logger.info("vision models ready")
        return _bundle


def warm() -> None:
    """Load the models ahead of the first request (called at app startup)."""
    try:
        load()
    except Exception:  # pragma: no cover - startup must not crash the server
        logger.exception("could not preload vision models; first scan will retry")
