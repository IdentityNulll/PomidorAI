"""Tests for the trained species head and its zero-shot fallback.

CLIP itself is stubbed: these cover the head's maths, the label mapping and
the fallback behaviour, none of which need the real weights.
"""

import numpy as np
import pytest

from app.vision import species


@pytest.fixture
def head_file(tmp_path, monkeypatch):
    """Point species at a small synthetic head with a known answer."""
    labels = ["apple", "tomato", species.DISTRACTOR]
    dimensions = 8

    # One clean basis direction per class, so the argmax is predictable.
    weights = np.zeros((dimensions, len(labels)), dtype=np.float32)
    for index in range(len(labels)):
        weights[index, index] = 10.0

    path = tmp_path / "species_head.npz"
    np.savez(path, weights=weights, bias=np.zeros(len(labels), dtype=np.float32),
             labels=np.array(labels))

    monkeypatch.setattr(species, "HEAD_FILE", path)
    species._head.cache_clear()

    # identify() blends the head with the prompts, so the zero-shot side needs
    # stubbing too. Uniform by default: it then cannot change the argmax, and
    # each test can override it to exercise the blend itself.
    monkeypatch.setattr(
        species,
        "identify_zero_shot",
        lambda _image: [(label, 1.0 / len(labels)) for label in labels],
    )

    yield labels, dimensions
    species._head.cache_clear()


def _point_at(index: int, dimensions: int) -> np.ndarray:
    vector = np.zeros(dimensions, dtype=np.float32)
    vector[index] = 1.0
    return vector


def test_head_is_used_when_weights_exist(head_file, monkeypatch):
    labels, dimensions = head_file
    monkeypatch.setattr(species, "_image_vector", lambda _i: _point_at(1, dimensions))

    ranked = species.identify(object())

    assert ranked[0][0] == "tomato"
    assert ranked[0][1] > 0.9


def test_head_can_return_the_distractor(head_file, monkeypatch):
    labels, dimensions = head_file
    monkeypatch.setattr(species, "_image_vector", lambda _i: _point_at(2, dimensions))

    assert species.identify(object())[0][0] == species.DISTRACTOR


def test_probabilities_are_a_distribution(head_file, monkeypatch):
    _labels, dimensions = head_file
    monkeypatch.setattr(species, "_image_vector", lambda _i: _point_at(0, dimensions))

    ranked = species.identify(object())

    assert sum(p for _, p in ranked) == pytest.approx(1.0, abs=1e-5)
    assert all(0.0 <= p <= 1.0 for _, p in ranked)
    assert ranked == sorted(ranked, key=lambda item: item[1], reverse=True)


def test_prompts_can_overturn_a_wrong_head_call(head_file, monkeypatch):
    """The blend exists for this case.

    On an unusual whole-plant photo the head can call a real crop
    "not a crop"; confident prompts pull the answer back.
    """
    labels, dimensions = head_file

    # Mirrors the real failure: head said not-a-crop 0.70 / tomato 0.26 on a
    # whole-plant tomato photo, while the prompts said tomato 0.99.
    vector = np.zeros(dimensions, dtype=np.float32)
    vector[1], vector[2] = 0.216, 0.315  # -> head probs ~ .03 / .26 / .70
    monkeypatch.setattr(species, "_image_vector", lambda _i: vector)
    monkeypatch.setattr(
        species,
        "identify_zero_shot",
        lambda _i: [("tomato", 0.99), ("apple", 0.005), (species.DISTRACTOR, 0.005)],
    )

    assert species.identify(object())[0][0] == "tomato"


def test_a_confident_head_is_not_overturned_by_weak_prompts(head_file, monkeypatch):
    """The head carries most of the weight (alpha 0.75), so it should hold."""
    labels, dimensions = head_file
    monkeypatch.setattr(species, "_image_vector", lambda _i: _point_at(1, dimensions))
    monkeypatch.setattr(
        species,
        "identify_zero_shot",
        lambda _i: [("apple", 0.4), ("tomato", 0.35), (species.DISTRACTOR, 0.25)],
    )

    assert species.identify(object())[0][0] == "tomato"


def test_blend_handles_a_label_the_prompts_never_emit(head_file, monkeypatch):
    """A missing prompt class must not crash or become NaN."""
    labels, dimensions = head_file
    monkeypatch.setattr(species, "_image_vector", lambda _i: _point_at(1, dimensions))
    monkeypatch.setattr(species, "identify_zero_shot", lambda _i: [("apple", 1.0)])

    ranked = species.identify(object())

    assert sum(p for _, p in ranked) == pytest.approx(1.0, abs=1e-5)
    assert all(p == p for _, p in ranked)  # no NaN


def test_falls_back_to_zero_shot_without_weights(tmp_path, monkeypatch):
    """A fresh checkout with no trained head must still work."""
    monkeypatch.setattr(species, "HEAD_FILE", tmp_path / "missing.npz")
    species._head.cache_clear()
    called = {}

    def fake_zero_shot(_image):
        called["yes"] = True
        return [("tomato", 0.7)]

    monkeypatch.setattr(species, "identify_zero_shot", fake_zero_shot)

    assert species.identify(object())[0][0] == "tomato"
    assert called == {"yes": True}
    species._head.cache_clear()


def test_head_labels_all_exist_in_plants_json(head_file):
    """Guards against a head trained on classes the app cannot render."""
    from app import analyzer

    _labels, _dimensions = head_file
    trained = species._head()[2]
    unknown = [
        label for label in trained
        if label != species.DISTRACTOR and label not in analyzer._PLANTS
    ]
    assert unknown == []
