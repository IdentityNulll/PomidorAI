"""Tests for the analyzer's routing policy.

These exercise the decision logic - which model is trusted for which kind of
photo, and when confidence is withheld - with the models stubbed out, so they
run in milliseconds. test_models.py covers the real weights.
"""

import pytest

from app import analyzer
from app.vision import disease as disease_model
from app.vision import species as species_model


@pytest.fixture
def fake_models(monkeypatch, tmp_path):
    """Replace both models with controllable stubs."""
    from PIL import Image

    path = tmp_path / "scan.jpg"
    Image.new("RGB", (64, 64), "green").save(path)

    state = {
        "clip": [("tomato", 0.9)],
        "leafy": 0.0,
        "crop": ("tomato", 0.9),
        "diseases": [{"label": "Fitoftoroz (kech kuyish)", "confidence": 0.8}],
        "fallback": [{"label": "Sog'lom", "confidence": 0.45}],
    }

    class Reading:
        def best_crop(self):
            return state["crop"]

    monkeypatch.setattr(species_model, "identify", lambda _i: state["clip"])
    monkeypatch.setattr(species_model, "leafiness", lambda _i: state["leafy"])
    monkeypatch.setattr(disease_model, "read_leaf", lambda _i: Reading())
    monkeypatch.setattr(disease_model, "from_reading", lambda _r, _p: state["diseases"])
    monkeypatch.setattr(disease_model, "clip_fallback", lambda _i, _p: state["fallback"])

    return state, str(path)


def test_non_leaf_photo_uses_clip(fake_models):
    state, path = fake_models
    state["clip"] = [("grape", 0.93)]
    state["leafy"] = 0.0

    result = analyzer.analyze(path)

    assert result["plant"]["id"] == "grape"
    assert result["plant"]["commonName"] == "Uzum"
    assert result["plant"]["confidence"] == 0.93


def test_leaf_photo_prefers_the_leaf_model_over_clip(fake_models):
    """CLIP reads most broad leaves as cotton; the leaf model must win."""
    state, path = fake_models
    state["clip"] = [("cotton", 0.88)]
    state["leafy"] = 0.95
    state["crop"] = ("potato", 0.84)

    result = analyzer.analyze(path)

    assert result["plant"]["id"] == "potato"
    assert result["plant"]["confidence"] == 0.84


def test_unconvincing_leaf_falls_back_to_clip_but_caps_confidence(fake_models):
    state, path = fake_models
    state["clip"] = [("cotton", 0.88)]
    state["leafy"] = 0.95
    state["crop"] = ("grape", 0.19)  # below CROP_MASS_REQUIRED

    result = analyzer.analyze(path)

    assert result["plant"]["id"] == "cotton"
    assert result["plant"]["confidence"] < analyzer.UNSURE_BELOW


def test_distractor_returns_no_name(fake_models):
    state, path = fake_models
    state["clip"] = [(species_model.DISTRACTOR, 0.97)]

    result = analyzer.analyze(path)

    assert result["plant"]["commonName"] == ""
    assert result["plant"]["confidence"] < analyzer.UNSURE_BELOW
    assert result["health"]["predictions"][0]["confidence"] < analyzer.UNSURE_BELOW
    assert result["info"]["description"] == ""


def test_disease_confidence_is_withheld_on_non_leaf_photos(fake_models):
    """A whole-plant shot is outside the disease model's training domain."""
    state, path = fake_models
    state["clip"] = [("tomato", 0.99)]
    state["leafy"] = 0.0
    state["diseases"] = [{"label": "Fitoftoroz (kech kuyish)", "confidence": 0.97}]

    result = analyzer.analyze(path)

    assert result["plant"]["confidence"] == 0.99
    assert result["health"]["predictions"][0]["confidence"] <= analyzer.UNSURE_CAP


def test_disease_confidence_survives_on_a_real_leaf(fake_models):
    state, path = fake_models
    state["clip"] = [("tomato", 0.5)]
    state["leafy"] = 0.95
    state["crop"] = ("tomato", 0.98)
    state["diseases"] = [{"label": "Fitoftoroz (kech kuyish)", "confidence": 0.97}]

    result = analyzer.analyze(path)

    assert result["health"]["predictions"][0]["confidence"] == 0.97


def test_uncovered_crop_uses_the_weak_fallback(fake_models):
    state, path = fake_models
    state["clip"] = [("wheat", 0.96)]
    state["leafy"] = 0.0

    result = analyzer.analyze(path)

    assert result["plant"]["id"] == "wheat"
    labels = [p["label"] for p in result["health"]["predictions"]]
    assert labels == ["Sog'lom"]


def test_health_is_unsure_when_the_species_is_a_guess(fake_models):
    """A diagnosis is only as good as the species it assumes."""
    state, path = fake_models
    state["clip"] = [("tomato", 0.30)]
    state["leafy"] = 0.0
    state["diseases"] = [{"label": "Fitoftoroz (kech kuyish)", "confidence": 0.99}]

    result = analyzer.analyze(path)

    assert result["health"]["predictions"][0]["confidence"] <= analyzer.UNSURE_CAP


def test_result_matches_the_api_contract(fake_models):
    _state, path = fake_models

    result = analyzer.analyze(path)

    assert set(result) == {"plant", "health", "info"}
    assert set(result["plant"]) == {"id", "commonName", "scientificName", "confidence"}
    assert set(result["info"]) == {
        "description", "howItGrows", "water", "sunlight",
        "soil", "season", "commonDiseases", "careTips",
    }
    assert isinstance(result["info"]["careTips"], list)
    for prediction in result["health"]["predictions"]:
        assert set(prediction) == {"label", "confidence"}
        assert 0.0 <= prediction["confidence"] <= 1.0


def test_every_plant_id_resolves(fake_models):
    """Each id the models can emit must exist in plants.json."""
    state, path = fake_models
    for plant_id in list(analyzer._PLANTS):
        state["clip"] = [(plant_id, 0.9)]
        state["leafy"] = 0.0
        assert analyzer.analyze(path)["plant"]["id"] == plant_id
