"""Train the species head: a linear probe over frozen CLIP features.

CLIP stays frozen and we fit a softmax classifier on its image embeddings.
That is cheap enough to train on CPU in minutes, and it beats hand-written
zero-shot prompts because it learns from actual photographs of these crops
instead of from a guess at what words describe them.

Low-resolution robustness is trained in, not hoped for: every image is also
embedded at reduced sizes with JPEG compression applied, so the head sees the
degraded features it will meet on a phone photo over slow mobile data.

    python backend/scripts/train_head.py

Writes app/vision/weights/species_head.npz (small enough to commit).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATASET = ROOT / "data" / "dataset"
OUT = ROOT / "app" / "vision" / "weights" / "species_head.npz"

# Each training image is embedded once per variant. "full" is the clean image;
# the rest simulate what actually reaches the server after the client resizes
# a phone photo and re-encodes it over a slow connection.
VARIANTS = [
    {"name": "full", "size": None, "quality": None},
    {"name": "640", "size": 640, "quality": 80},
    {"name": "320", "size": 320, "quality": 70},
    {"name": "160", "size": 160, "quality": 60},
]


def degrade(image: Image.Image, size: int | None, quality: int | None) -> Image.Image:
    """Downscale and re-encode, mimicking a low-resolution upload."""
    out = image
    if size:
        out = out.copy()
        out.thumbnail((size, size), Image.Resampling.LANCZOS)
    if quality:
        buffer = BytesIO()
        out.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        out = Image.open(buffer).convert("RGB")
    return out


def load_paths() -> tuple[list[Path], list[str], list[str]]:
    labels = sorted(d.name for d in DATASET.iterdir() if d.is_dir())
    paths, targets = [], []
    for label in labels:
        for path in sorted((DATASET / label).glob("*.jpg")):
            paths.append(path)
            targets.append(label)
    return paths, targets, labels


CACHE = ROOT / "data" / "embeddings.npz"
BATCH = 32


def _embed_batch(bundle, images) -> np.ndarray:
    """One CLIP forward pass over a batch of PIL images."""
    inputs = bundle.clip_processor(images=images, return_tensors="pt")
    features = bundle.clip.get_image_features(**inputs)
    features = features.pooler_output if hasattr(features, "pooler_output") else features
    features = features / features.norm(dim=-1, keepdim=True)
    return features.numpy().astype(np.float32)


def embed_all(paths, targets, labels, split_seed=0, test_fraction=0.2, use_cache=True):
    """Embed every image at every variant; split by image, not by variant.

    Splitting by image matters: variants of one photo are near-duplicates, and
    letting them straddle the split would leak the test set into training and
    report an accuracy the model does not have.

    Results are cached, because embedding is the slow part and the training
    step after it is worth re-running on its own.
    """
    if use_cache and CACHE.exists():
        blob = np.load(CACHE, allow_pickle=True)
        if list(blob["labels"]) == labels and int(blob["count"]) == len(paths):
            print(f"  reusing cached embeddings ({CACHE})")
            return (blob["train_x"], blob["train_y"]), (blob["test_x"], blob["test_y"])
        print("  cache is stale, re-embedding")

    from app.vision.models import load

    bundle = load()

    random.seed(split_seed)
    indices = list(range(len(paths)))
    random.shuffle(indices)
    test_ids = set(indices[: int(len(indices) * test_fraction)])
    label_to_index = {label: i for i, label in enumerate(labels)}

    # Build the full work list first so it can be fed through in batches.
    jobs = []  # (split, image, label_index)
    for position, (path, target) in enumerate(zip(paths, targets)):
        try:
            with Image.open(path) as handle:
                image = handle.convert("RGB")
        except Exception:
            continue

        split = "test" if position in test_ids else "train"
        # The test set only needs the clean variant here; per-resolution
        # accuracy is measured separately by evaluate_head.py.
        variants = VARIANTS if split == "train" else VARIANTS[:1]
        for variant in variants:
            try:
                jobs.append((
                    split,
                    degrade(image, variant["size"], variant["quality"]),
                    label_to_index[target],
                ))
            except Exception:
                continue

    print(f"  {len(jobs)} embeddings to compute in batches of {BATCH}")
    rows = {"train": [], "test": []}
    for start in range(0, len(jobs), BATCH):
        chunk = jobs[start : start + BATCH]
        vectors = _embed_batch(bundle, [job[1] for job in chunk])
        for (split, _image, answer), vector in zip(chunk, vectors):
            rows[split].append((vector, answer))
        if start % (BATCH * 10) == 0:
            print(f"  {start}/{len(jobs)}", flush=True)

    def stack(key):
        return (
            np.stack([r[0] for r in rows[key]]).astype(np.float32),
            np.array([r[1] for r in rows[key]], dtype=np.int64),
        )

    (train_x, train_y), (test_x, test_y) = stack("train"), stack("test")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        CACHE, train_x=train_x, train_y=train_y, test_x=test_x, test_y=test_y,
        labels=np.array(labels), count=len(paths),
    )
    return (train_x, train_y), (test_x, test_y)


def train_softmax(features, answers, classes, epochs=4000, learning_rate=10.0, weight_decay=1e-4):
    """Multinomial logistic regression, full-batch gradient descent + momentum.

    CLIP features are L2-normalised, so gradients are small and a timid
    learning rate leaves the model badly undertrained - the first run here
    stopped at 70.7% with the loss still falling. Momentum plus a much larger
    step size converges properly in the same wall-clock time.
    """
    rng = np.random.default_rng(0)
    weights = rng.normal(0, 0.01, (features.shape[1], classes)).astype(np.float32)
    bias = np.zeros(classes, dtype=np.float32)
    onehot = np.eye(classes, dtype=np.float32)[answers]

    # Class-balanced sample weights. The negative class is roughly twice the
    # size of any single crop, and unweighted training let it swallow genuine
    # crop photos - a tomato plant came back "not a crop" at 0.80.
    counts = np.bincount(answers, minlength=classes).astype(np.float32)
    class_weight = len(answers) / (classes * np.maximum(counts, 1.0))
    sample_weight = class_weight[answers].astype(np.float32)
    sample_weight /= sample_weight.mean()
    sample_weight = sample_weight[:, None]

    weight_velocity = np.zeros_like(weights)
    bias_velocity = np.zeros_like(bias)
    momentum = 0.9

    for epoch in range(epochs):
        logits = features @ weights + bias
        logits -= logits.max(axis=1, keepdims=True)
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum(axis=1, keepdims=True)

        error = (probabilities - onehot) * sample_weight / len(features)
        weight_gradient = features.T @ error + weight_decay * weights
        bias_gradient = error.sum(axis=0)

        weight_velocity = momentum * weight_velocity + weight_gradient
        bias_velocity = momentum * bias_velocity + bias_gradient
        weights -= learning_rate * weight_velocity
        bias -= learning_rate * bias_velocity

        if epoch % 500 == 0 or epoch == epochs - 1:
            loss = -np.log(probabilities[np.arange(len(answers)), answers] + 1e-9).mean()
            print(f"  epoch {epoch:>5}  loss {loss:.4f}", flush=True)

    return weights, bias


def accuracy(features, answers, weights, bias) -> float:
    return float(((features @ weights + bias).argmax(axis=1) == answers).mean())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=4000)
    args = parser.parse_args()

    if not DATASET.exists():
        print("no dataset; run backend/scripts/fetch_dataset.py first")
        return 1

    paths, targets, labels = load_paths()
    print(f"{len(paths)} images across {len(labels)} classes")

    (train_x, train_y), (test_x, test_y) = embed_all(paths, targets, labels)
    print(f"train rows {len(train_x)} (with degraded variants), test rows {len(test_x)}")

    weights, bias = train_softmax(train_x, train_y, len(labels), epochs=args.epochs)

    print(f"\ntrain accuracy {accuracy(train_x, train_y, weights, bias):.3f}")
    print(f"test  accuracy {accuracy(test_x, test_y, weights, bias):.3f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez(OUT, weights=weights, bias=bias, labels=np.array(labels))
    print(f"\nsaved {OUT} ({OUT.stat().st_size // 1024} KB)")

    (OUT.parent / "dataset_counts.json").write_text(
        json.dumps({label: targets.count(label) for label in labels}, indent=2)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
