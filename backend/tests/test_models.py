"""Smoke tests against the real model weights.

Skipped by default: they load ~1 GB and take tens of seconds. Run with

    POMIDORAI_MODEL_TESTS=1 pytest tests/test_models.py

Accuracy on real photographs is tracked by hand (see the README); these only
guarantee the plumbing works and the contract holds with live models.
"""

import os

import pytest
from PIL import Image

pytestmark = pytest.mark.skipif(
    os.environ.get("POMIDORAI_MODEL_TESTS") != "1",
    reason="set POMIDORAI_MODEL_TESTS=1 to run tests against the real weights",
)


@pytest.fixture(scope="module")
def loaded():
    from app.vision.models import load

    return load()


def test_models_load(loaded):
    assert loaded.clip is not None
    assert len(loaded.disease_labels) == 38


def test_every_label_the_model_emits_has_a_library_entry(loaded):
    """A label with no entry would surface to the farmer as a raw slug."""
    from app.vision.guide import known_slugs
    from app.vision.labels import DISEASE_SLUG

    library = known_slugs()
    unmapped = sorted(l for l in loaded.disease_labels.values() if l not in DISEASE_SLUG)
    assert unmapped == [], f"labels with no slug: {unmapped}"

    missing = sorted({s for s in DISEASE_SLUG.values() if s not in library})
    assert missing == [], f"slugs with no library entry: {missing}"


def test_analyze_returns_the_contract_on_a_real_image(tmp_path):
    from app.analyzer import analyze

    path = tmp_path / "scan.jpg"
    Image.new("RGB", (640, 480), (40, 120, 60)).save(path)

    result = analyze(str(path))

    assert set(result) == {"view", "plant", "health", "info"}
    assert 0.0 <= result["plant"]["confidence"] <= 1.0
    assert 1 <= len(result["health"]["predictions"]) <= 5


def test_analyze_works_off_the_thread_that_loaded_the_models(tmp_path):
    """Regression: grad mode is thread-local in PyTorch.

    The models are loaded during app startup, but requests are served from
    other threadpool threads. Disabling grad globally at load time only
    covered the loading thread, so every real scan raised
    "Can't call numpy() on Tensor that requires grad" - while passing every
    single-threaded test and CLI run.
    """
    from concurrent.futures import ThreadPoolExecutor

    from app.analyzer import analyze
    from app.vision.models import load

    load()  # load here, so the worker below is a different thread

    path = tmp_path / "scan.jpg"
    Image.new("RGB", (400, 300), (60, 130, 70)).save(path)

    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(analyze, str(path)).result()

    assert set(result) == {"view", "plant", "health", "info"}


def test_noise_is_not_confidently_called_a_crop(tmp_path):
    """A photo that is not a crop must not come back with a confident name."""
    import random

    from app.analyzer import UNSURE_BELOW, analyze

    random.seed(0)
    image = Image.new("RGB", (320, 320))
    image.putdata([
        (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        for _ in range(320 * 320)
    ])
    path = tmp_path / "noise.jpg"
    image.save(path)

    result = analyze(str(path))

    assert result["plant"]["confidence"] < UNSURE_BELOW


def test_labelled_garden_photos_do_not_regress(tmp_path):
    """Accuracy floor on the owner's own labelled photos.

    Prompt edits routinely fix one photo and break two others; only a scored
    set catches that. Baseline when written: 15/20. The floor is set just
    below so a real regression fails while noise does not.

    Skipped unless the photos are present - they are personal and not in the
    repo. Point POMIDORAI_GARDEN_DIR at them to run this.
    """
    import json
    from pathlib import Path

    directory = Path(
        os.environ.get(
            "POMIDORAI_GARDEN_DIR",
            Path.home() / "Documents" / "pomidorai-test-images" / "newtests",
        )
    )
    if not directory.is_dir():
        pytest.skip(f"no labelled photos at {directory}")

    from app.analyzer import analyze
    from app.vision.thresholds import UNSURE_BELOW

    truth_file = Path(__file__).parent / "data" / "garden_truth.json"
    truth = json.loads(truth_file.read_text())["labels"]
    files = sorted(directory.glob("*.jpg"))

    correct = 0
    for index, expected in truth.items():
        result = analyze(str(files[int(index) - 1]))
        plant = result["plant"]
        got = plant["id"] if plant["confidence"] >= UNSURE_BELOW else ""
        correct += got == expected

    assert correct >= 14, f"{correct}/{len(truth)} - regression against the 15/20 baseline"
