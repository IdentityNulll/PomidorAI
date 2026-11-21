"""Tests for learning from user corrections.

The nearest-neighbour maths and the API contract, with CLIP stubbed.
"""

import numpy as np
import pytest

from app.vision import memory
from tests.conftest import make_image


def _vector(*values) -> np.ndarray:
    """A unit vector in the first len(values) dimensions."""
    array = np.zeros(8, dtype=np.float32)
    array[: len(values)] = values
    return array / np.linalg.norm(array)


@pytest.fixture
def stub_clip(monkeypatch):
    """Control exactly what CLIP 'sees' for the image under test."""
    holder = {"vector": _vector(1, 0)}
    monkeypatch.setattr(memory, "_image_vector", lambda _image: holder["vector"])
    return holder


def test_no_corrections_means_no_recall(stub_clip):
    assert memory.recall(object(), []) is None


def test_a_close_match_is_recalled(stub_clip):
    """One correction is enough - that is the point of nearest-neighbour."""
    stored = [("pepper", _vector(1, 0.05).tobytes())]

    result = memory.recall(object(), stored)

    assert result is not None
    plant_id, confidence = result
    assert plant_id == "pepper"
    assert confidence > memory.MATCH_THRESHOLD


def test_a_distant_photo_is_not_recalled(stub_clip):
    """A correction about peppers must not hijack a photo of a rose."""
    stored = [("pepper", _vector(0, 1).tobytes())]

    assert memory.recall(object(), stored) is None


def test_the_closest_correction_wins(stub_clip):
    stored = [
        ("quince", _vector(0.8, 0.6).tobytes()),
        ("pepper", _vector(1, 0.02).tobytes()),
    ]

    plant_id, _confidence = memory.recall(object(), stored)

    assert plant_id == "pepper"


def test_agreeing_neighbours_raise_confidence(stub_clip):
    """Vectors just over the threshold, so the cap leaves headroom."""
    one = memory.recall(object(), [("pepper", _vector(1, 0.40).tobytes())])
    many = memory.recall(
        object(),
        [
            ("pepper", _vector(1, 0.40).tobytes()),
            ("pepper", _vector(1, 0.39).tobytes()),
            ("pepper", _vector(1, 0.38).tobytes()),
        ],
    )

    assert one[1] < memory.MAX_CONFIDENCE  # otherwise the test proves nothing
    assert many[1] > one[1]


def test_confidence_is_capped(stub_clip):
    """A correction is evidence, not proof."""
    stored = [("pepper", _vector(1, 0).tobytes())] * 10

    _plant_id, confidence = memory.recall(object(), stored)

    assert confidence <= memory.MAX_CONFIDENCE


def test_encode_round_trips(monkeypatch):
    monkeypatch.setattr(memory, "_image_vector", lambda _i: _vector(0.6, 0.8))

    restored = memory.decode(memory.encode(object()))

    assert restored.dtype == np.float32
    assert np.allclose(restored, _vector(0.6, 0.8))


def test_correcting_a_scan_updates_it_and_is_remembered(client, monkeypatch):
    """End to end: correct a scan, and the stored scan reflects it."""
    monkeypatch.setattr("app.corrections._embed_scan", lambda _path: _vector(1, 0).tobytes())

    created = client.post("/api/analyze", files={"image": ("a.jpg", make_image(), "image/jpeg")})
    scan_id = created.json()["id"]
    assert created.json()["plant"]["id"] == "tomato"

    corrected = client.post(f"/api/scans/{scan_id}/correct", json={"plantId": "pepper"})

    assert corrected.status_code == 200
    assert corrected.json()["plant"]["commonName"] == "Qalampir"
    # The info card must follow the corrected plant, not stay on tomato.
    assert "qalampir" in corrected.json()["info"]["description"].lower()

    reopened = client.get(f"/api/scans/{scan_id}")
    assert reopened.json()["plant"]["id"] == "pepper"


def test_correcting_to_an_unknown_plant_is_rejected(client, monkeypatch):
    monkeypatch.setattr("app.corrections._embed_scan", lambda _path: _vector(1, 0).tobytes())
    created = client.post("/api/analyze", files={"image": ("a.jpg", make_image(), "image/jpeg")})

    response = client.post(
        f"/api/scans/{created.json()['id']}/correct", json={"plantId": "not-a-plant"}
    )

    assert response.status_code == 400


def test_another_session_cannot_correct_your_scan(client, monkeypatch):
    monkeypatch.setattr("app.corrections._embed_scan", lambda _path: _vector(1, 0).tobytes())
    created = client.post("/api/analyze", files={"image": ("a.jpg", make_image(), "image/jpeg")})
    scan_id = created.json()["id"]

    client.cookies.clear()
    response = client.post(f"/api/scans/{scan_id}/correct", json={"plantId": "pepper"})

    assert response.status_code == 404


def test_a_correction_does_not_leak_onto_a_similar_but_different_plant(stub_clip):
    """Regression: peach corrections relabelled five quince photos.

    All the autumn-branch photos from one garden sit close together in CLIP
    space. At a 0.80 threshold a peach correction matched quince photos at
    up to 0.90 and overwrote them at 0.95 confidence - fixing two photos and
    breaking five.
    """
    stub_clip["vector"] = _vector(1, 0.45)  # ~0.91 similarity: close, not the same
    stored = [("peach", _vector(1, 0).tobytes())]

    assert memory.recall(object(), stored) is None


def test_a_near_tie_between_two_labels_does_not_fire(stub_clip):
    """Two crops equally similar is evidence for neither."""
    stub_clip["vector"] = _vector(1, 0)
    stored = [
        ("peach", _vector(1, 0.01).tobytes()),
        ("quince", _vector(1, 0.012).tobytes()),
    ]

    assert memory.recall(object(), stored) is None
