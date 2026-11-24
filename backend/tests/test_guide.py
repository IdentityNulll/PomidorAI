"""The disease library and the plain-language content.

These guard the data, not the models: a missing slug or an empty field would
reach a farmer as a blank card.
"""

import json
from pathlib import Path

import pytest

from app.vision import guide
from app.vision.labels import CROP_BY_PLANT_ID, DISEASE_SLUG, HEALTHY_SLUG

DATA = Path(__file__).parent.parent / "app" / "data"
PLANTS = json.loads((DATA / "plants.json").read_text(encoding="utf-8"))
LIBRARY = {
    slug: entry
    for slug, entry in json.loads((DATA / "diseases.json").read_text(encoding="utf-8")).items()
    if not slug.startswith("_")
}


def test_every_model_label_maps_to_a_real_entry():
    """A label with no entry would render as a bare slug in the UI."""
    missing = sorted({s for s in DISEASE_SLUG.values() if s not in LIBRARY})
    assert missing == []


def test_every_crop_disease_reference_resolves():
    """plants.json lists slugs now, not free text - they must all exist."""
    bad = [
        (plant["id"], slug)
        for plant in PLANTS
        for slug in plant["commonDiseases"]
        if slug not in LIBRARY
    ]
    assert bad == []


@pytest.mark.parametrize("slug", sorted(LIBRARY))
def test_entry_is_complete_and_useful(slug):
    entry = LIBRARY[slug]
    assert entry["name"].strip(), f"{slug} has no name"
    assert entry["whatIsIt"].strip(), f"{slug} does not say what it is"
    assert entry["signs"], f"{slug} has no recognisable signs"
    # "noaniq" is the honest I-don't-know card and has nothing to prevent.
    if slug not in {"noaniq", HEALTHY_SLUG}:
        assert entry["whatToDo"], f"{slug} has no advice"
        assert entry["prevent"], f"{slug} has no prevention advice"


@pytest.mark.parametrize("slug", sorted(LIBRARY))
def test_advice_names_no_chemicals(slug):
    """Safety: wrong pesticide advice is worse than none.

    The library sticks to cultural practice and defers chemical choice to an
    agronomist, who can account for the crop, the dose and the local rules.
    """
    import re

    # Product names can be plain substrings; units need word boundaries,
    # because "ml" happens to sit inside ordinary words like "namlik".
    products = ["mis kuporos", "bordo", "karbofos", "aktellik", "fundazol", "konfidor"]
    units = [r"\d+\s*ml\b", r"\d+\s*g\b", r"\bgramm\b", r"\blitr", r"foizli eritma"]

    text = " ".join(entry_texts(LIBRARY[slug])).lower()
    hits = [p for p in products if p in text]
    hits += [u for u in units if re.search(u, text)]
    assert hits == [], f"{slug} names a chemical or a dose: {hits}"


def entry_texts(entry: dict) -> list[str]:
    out = [entry["name"], entry.get("alsoCalled", ""), entry["whatIsIt"], entry.get("whyItHappens", "")]
    for key in ("signs", "whatToDo", "prevent"):
        out.extend(entry.get(key, []))
    return out


@pytest.mark.parametrize("plant", PLANTS, ids=lambda p: p["id"])
def test_plant_card_is_plain_language(plant):
    """Written for a farmer, not a botanist.

    Checks the two things that actually made the old text hard: Latin names
    buried in the prose, and sentences long enough to lose the reader.
    """
    prose = " ".join(
        [plant["description"], plant["howItGrows"], plant["water"],
         plant["sunlight"], plant["soil"]]
    )
    assert plant["scientificName"] not in prose, "Latin name belongs in its own field"

    longest = max(len(s.strip()) for s in prose.replace("!", ".").split(".") if s.strip())
    assert longest <= 160, f"a sentence is {longest} characters - split it"


@pytest.mark.parametrize("plant", PLANTS, ids=lambda p: p["id"])
def test_plant_card_has_every_field_filled(plant):
    for key in ("description", "howItGrows", "water", "sunlight", "soil", "season"):
        assert plant[key].strip(), f"{plant['id']}.{key} is empty"
    assert len(plant["careTips"]) >= 2, f"{plant['id']} needs more than one tip"
    assert plant["commonDiseases"], f"{plant['id']} lists no diseases"


def test_describe_disease_always_returns_the_full_shape():
    """The frontend reads these keys unconditionally."""
    for slug in (*sorted(LIBRARY), "a-slug-that-does-not-exist"):
        prediction = guide.describe_disease(slug, 0.5)
        assert set(prediction) >= {
            "slug", "label", "confidence",
            "alsoCalled", "whatIsIt", "signs", "whyItHappens", "whatToDo", "prevent",
        }
        assert isinstance(prediction["signs"], list)


def test_crops_with_a_disease_model_list_what_it_can_find():
    """If the model can name a disease for a crop, the card should too."""
    by_id = {plant["id"]: plant for plant in PLANTS}
    for plant_id, crop in CROP_BY_PLANT_ID.items():
        plant = by_id.get(plant_id)
        if not plant:
            continue  # squash, orange and friends are not curated crops
        detectable = {
            slug
            for label, slug in DISEASE_SLUG.items()
            if label.startswith(f"{crop}___") and slug != HEALTHY_SLUG
        }
        listed = set(plant["commonDiseases"])
        assert detectable <= listed, (
            f"{plant_id} can be diagnosed with {sorted(detectable - listed)} "
            "but does not list them"
        )
