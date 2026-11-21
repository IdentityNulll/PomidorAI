"""Tests for the analyzer's routing policy.

Which model is trusted for which kind of photo, and when confidence is
withheld. The models are stubbed, so these run in milliseconds;
test_models.py covers the real weights.
"""

import pytest

from app import analyzer
from app.vision import disease as disease_model
from app.vision import names
from app.vision import plantnet
from app.vision import gates as clip_gate


@pytest.fixture
def fake_models(monkeypatch, tmp_path):
    """Replace every model with a controllable stub."""
    from PIL import Image

    path = tmp_path / "scan.jpg"
    Image.new("RGB", (64, 64), "green").save(path)

    state = {
        "plantness": 0.9,
        "species": [("Solanum lycopersicum", 0.9)],
        "leafy": 0.0,
        "crop": ("tomato", 0.9),
        "diseases": [{"label": "Fitoftoroz (kech kuyish)", "confidence": 0.8}],
        "fallback": [{"label": "Sog'lom", "confidence": 0.45}],
    }

    class Reading:
        def best_crop(self):
            return state["crop"]

    monkeypatch.setattr(clip_gate, "plantness",
                        lambda _i: [("plant", state["plantness"]),
                                    ("not_plant", 1 - state["plantness"])])
    monkeypatch.setattr(clip_gate, "leafiness", lambda _i: state["leafy"])
    monkeypatch.setattr(plantnet, "identify", lambda _i, top=5: state["species"])
    monkeypatch.setattr(disease_model, "read_leaf", lambda _i: Reading())
    monkeypatch.setattr(disease_model, "from_reading", lambda _r, _p: state["diseases"])
    monkeypatch.setattr(disease_model, "clip_fallback",
                        lambda _i, _p, _s="": state["fallback"])

    return state, str(path)


def test_curated_crop_gets_its_uzbek_card(fake_models):
    state, path = fake_models
    state["species"] = [("Cydonia oblonga", 0.73)]

    result = analyzer.analyze(path)

    assert result["plant"]["commonName"] == "Behi"
    assert result["plant"]["confidence"] == 0.73
    assert result["info"]["water"]  # full agronomy card present


def test_uncurated_species_still_gets_an_uzbek_name(fake_models):
    """7806 species, 19 curated cards - the rest lean on Wikidata."""
    state, path = fake_models
    state["species"] = [("Rosa glauca", 0.6)]

    result = analyzer.analyze(path)

    assert result["plant"]["scientificName"] == "Rosa glauca"
    assert result["plant"]["commonName"]  # genus fallback -> Itburun
    assert result["info"]["water"] == ""  # no invented agronomy advice


def test_non_plant_is_rejected_before_the_species_model(fake_models):
    """PlantNet names a species for a car; the CLIP gate has to stop it."""
    state, path = fake_models
    state["plantness"] = 0.05

    result = analyzer.analyze(path)

    assert result["plant"]["commonName"] == ""
    assert result["plant"]["scientificName"] == ""
    assert result["plant"]["confidence"] < analyzer.UNSURE_BELOW


def test_leaf_model_cannot_override_a_confident_species(fake_models):
    """Regression: the leaf model has 14 classes and cannot abstain.

    On a beet leaf it confidently answers "Tomato", which used to turn a
    correct "Lavlagi 0.86" into "Pomidor 0.69".
    """
    state, path = fake_models
    state["species"] = [("Beta vulgaris", 0.66)]
    state["leafy"] = 0.95
    state["crop"] = ("tomato", 0.92)

    result = analyzer.analyze(path)

    assert result["plant"]["commonName"] == "Lavlagi"
    assert result["plant"]["confidence"] == 0.66


def test_leaf_model_may_correct_an_unsure_species(fake_models):
    state, path = fake_models
    state["species"] = [("Paulownia tomentosa", 0.08)]
    state["leafy"] = 0.95
    state["crop"] = ("tomato", 0.95)

    result = analyzer.analyze(path)

    assert result["plant"]["scientificName"] == "Solanum lycopersicum"


def test_agreement_between_models_raises_confidence(fake_models):
    state, path = fake_models
    state["species"] = [("Solanum lycopersicum", 0.40)]
    state["leafy"] = 0.95
    state["crop"] = ("tomato", 0.97)

    assert analyzer.analyze(path)["plant"]["confidence"] == 0.97


def test_disease_is_withheld_on_non_leaf_photos(fake_models):
    state, path = fake_models
    state["species"] = [("Solanum lycopersicum", 0.99)]
    state["leafy"] = 0.0
    state["diseases"] = [{"label": "Fitoftoroz (kech kuyish)", "confidence": 0.97}]

    result = analyzer.analyze(path)

    assert result["plant"]["confidence"] == 0.99
    assert result["health"]["predictions"][0]["confidence"] <= analyzer.UNSURE_CAP


def test_disease_survives_on_a_real_leaf(fake_models):
    state, path = fake_models
    state["species"] = [("Solanum lycopersicum", 0.8)]
    state["leafy"] = 0.95
    state["crop"] = ("tomato", 0.98)
    state["diseases"] = [{"label": "Fitoftoroz (kech kuyish)", "confidence": 0.97}]

    assert analyzer.analyze(path)["health"]["predictions"][0]["confidence"] == 0.97


def test_wild_species_never_gets_a_confident_diagnosis(fake_models):
    """No disease model and no trustworthy prompts for an arbitrary plant."""
    state, path = fake_models
    state["species"] = [("Paulownia tomentosa", 0.95)]

    predictions = analyzer.analyze(path)["health"]["predictions"]

    assert all(p["confidence"] <= analyzer.UNSURE_CAP for p in predictions)


def test_newly_covered_crop_uses_the_real_disease_model(fake_models):
    """Pepper was the gap that prompted widening to all 14 crops."""
    state, path = fake_models
    state["species"] = [("Capsicum annuum", 0.8)]
    state["leafy"] = 0.95
    state["crop"] = ("pepper", 0.9)
    state["diseases"] = [{"label": "Bakterial dog'lanish", "confidence": 0.88}]

    result = analyzer.analyze(path)

    assert result["plant"]["commonName"] == "Qalampir"
    assert result["health"]["predictions"][0]["confidence"] == 0.88


def test_result_matches_the_api_contract(fake_models):
    _state, path = fake_models

    result = analyzer.analyze(path)

    assert set(result) == {"plant", "health", "info"}
    assert set(result["plant"]) == {"id", "commonName", "scientificName", "confidence"}
    assert set(result["info"]) == set(analyzer.EMPTY_INFO)
    assert isinstance(result["info"]["careTips"], list)
    for prediction in result["health"]["predictions"]:
        assert set(prediction) == {"label", "confidence"}
        assert 0.0 <= prediction["confidence"] <= 1.0


def test_every_curated_crop_resolves(fake_models):
    """Each curated scientific name must round-trip through analyze()."""
    state, path = fake_models
    for scientific, entry in names._plants().items():
        state["species"] = [(scientific, 0.9)]
        state["leafy"] = 0.0
        assert analyzer.analyze(path)["plant"]["commonName"] == entry["commonName"]
