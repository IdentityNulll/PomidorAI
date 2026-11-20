"""Compare the trained species head against zero-shot prompts.

Reports accuracy at full resolution and at progressively smaller sizes, which
is the number that matters for phone photos over slow mobile data.

    python backend/scripts/evaluate_head.py

Uses the same image-level split as train_head.py, so the test images here are
ones the head never trained on.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATASET = ROOT / "data" / "dataset"
WEIGHTS = ROOT / "app" / "vision" / "weights" / "species_head.npz"

RESOLUTIONS = [None, 640, 320, 160, 96]


def degrade(image: Image.Image, size: int | None) -> Image.Image:
    """Downscale and re-encode, matching train_head.py's degradation."""
    from io import BytesIO

    out = image
    if size:
        out = out.copy()
        out.thumbnail((size, size), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        out.save(buffer, format="JPEG", quality=max(55, min(85, size // 6)))
        buffer.seek(0)
        out = Image.open(buffer).convert("RGB")
    return out


def test_split(test_fraction=0.2, split_seed=0):
    """Reproduce train_head.py's split and return only the held-out images."""
    labels = sorted(d.name for d in DATASET.iterdir() if d.is_dir())
    paths, targets = [], []
    for label in labels:
        for path in sorted((DATASET / label).glob("*.jpg")):
            paths.append(path)
            targets.append(label)

    random.seed(split_seed)
    indices = list(range(len(paths)))
    random.shuffle(indices)
    cut = int(len(indices) * test_fraction)
    held_out = set(indices[:cut])

    return [(paths[i], targets[i]) for i in sorted(held_out)], labels


def main() -> int:
    from app.vision import species
    from app.vision.models import load

    if not WEIGHTS.exists():
        print("no trained head; run backend/scripts/train_head.py first")
        return 1

    bundle = load()
    blob = np.load(WEIGHTS, allow_pickle=True)
    weights, bias = blob["weights"], blob["bias"]
    head_labels = list(blob["labels"])

    samples, _labels = test_split()
    print(f"{len(samples)} held-out images\n")
    print(f"{'resolution':>12} {'zero-shot':>11} {'head only':>11} {'production':>12}")
    print("-" * 50)

    for size in RESOLUTIONS:
        zero_hits = head_hits = live_hits = total = 0
        for path, truth in samples:
            try:
                with Image.open(path) as handle:
                    image = degrade(handle.convert("RGB"), size)
            except Exception:
                continue
            total += 1

            if species.identify_zero_shot(image)[0][0] == truth:
                zero_hits += 1

            # Head on its own, bypassing the blend.
            vector = species._image_vector(image)
            if head_labels[int((vector @ weights + bias).argmax())] == truth:
                head_hits += 1

            # What the app actually runs: head blended with the prompts.
            if species.identify(image)[0][0] == truth:
                live_hits += 1

        name = "full" if size is None else f"{size}px"
        print(
            f"{name:>12} {zero_hits / total:>10.1%} {head_hits / total:>10.1%}"
            f" {live_hits / total:>11.1%}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
