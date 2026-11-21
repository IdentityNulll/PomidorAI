"""Turning a scientific name into something an Uzbek farmer can read.

Three tiers, best first:

1. A curated crop in data/plants.json - full Uzbek agronomy card.
2. A Wikidata Uzbek label (data/uz_species.json, built offline from CC0 data)
   - correct Uzbek name, but no agronomy advice we can vouch for.
3. Neither - show the scientific name alone and say so.

Tier 3 is deliberately honest rather than inventive: the model knows 7806
species and we are not going to pretend to have Uzbek growing advice for all
of them.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data"
PLANTS_FILE = Path(__file__).parent.parent / "data" / "plants.json"
UZ_FILE = DATA / "uz_species.json"


@lru_cache(maxsize=1)
def _plants() -> dict[str, dict]:
    """Curated crops keyed by scientific name."""
    with PLANTS_FILE.open(encoding="utf-8") as handle:
        return {p["scientificName"]: p for p in json.load(handle)}


@lru_cache(maxsize=1)
def _uz() -> dict[str, dict]:
    if not UZ_FILE.exists():
        return {}
    with UZ_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def curated(scientific: str) -> dict | None:
    """The full plants.json entry for a scientific name, if we wrote one."""
    return _plants().get(scientific)


@lru_cache(maxsize=1)
def _by_id() -> dict[str, dict]:
    return {p["id"]: p for p in _plants().values()}


def by_plant_id(plant_id: str) -> dict | None:
    """The curated entry for a plants.json id, if there is one."""
    return _by_id().get(plant_id)


def uzbek_name(scientific: str) -> str | None:
    """Uzbek common name from Wikidata, or the genus' name as a fallback.

    A genus match is a real improvement over a bare Latin binomial: knowing a
    plant is a rose ("Atirgul") is useful even when the exact species is not
    in Wikidata.
    """
    table = _uz()
    genus = scientific.split(" ")[0]

    entry = table.get(scientific) or {}
    label = entry.get("uz")
    if label and not _is_latin(label, genus):
        return _tidy(label)

    for name, other in table.items():
        label = other.get("uz")
        if label and name.split(" ")[0] == genus and not _is_latin(label, genus):
            return _tidy(label)
    return None


def _is_latin(label: str, genus: str) -> bool:
    """Wikidata often stores the Latin binomial as the 'uz' label.

    Showing "Rosa banksiae" as if it were the Uzbek name is worse than
    showing nothing, and the genus fallback used to spread one such label
    across every species in the genus.
    """
    return label.split(" ")[0].strip().lower() == genus.lower()


def describe(scientific: str) -> str | None:
    """Short Uzbek description from Wikidata, when there is one."""
    entry = _uz().get(scientific) or {}
    description = entry.get("desc")
    return description.strip() if description else None


def _tidy(label: str) -> str:
    """Wikidata labels arrive inconsistently cased; make them presentable."""
    label = label.strip()
    # Normalise the Cyrillic-looking apostrophes Wikidata often carries.
    label = label.replace("ʻ", "'").replace("‘", "'").replace("’", "'")
    return label[:1].upper() + label[1:] if label else label


def coverage() -> dict[str, int]:
    """Counts used by tests and the README, not at runtime."""
    table = _uz()
    return {
        "curated_crops": len(_plants()),
        "species_with_uzbek_name": sum(1 for v in table.values() if v.get("uz")),
        "species_known": len(table),
    }


@lru_cache(maxsize=1)
def _id_by_scientific() -> dict[str, str]:
    return {sci: entry["id"] for sci, entry in _plants().items()}


def id_for_scientific(scientific: str) -> str | None:
    """plants.json id for a scientific name, if we curate that crop."""
    return _id_by_scientific().get(scientific)
