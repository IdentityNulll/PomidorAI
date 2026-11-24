"""The disease library: what a diagnosis actually means to a farmer.

A label and a percentage are not useful on their own. "Fitoftoroz 98%" tells
someone nothing about what to look at or what to do this afternoon. Every
prediction therefore carries the whole entry from data/diseases.json: what
the disease is, how to recognise it, why it showed up, what to do now and
how to avoid it next season.

The text is deliberately plain - the reader is a farmer, not a biologist.
Advice is cultural practice only (cut, clear, water differently, rotate).
No chemical names or doses: choosing those wrongly is dangerous, and an
agronomist should make that call.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DISEASES_FILE = Path(__file__).parent.parent / "data" / "diseases.json"

# Shape every prediction carries, so the frontend can rely on the keys
# existing even for a disease we have no entry for.
EMPTY = {
    "alsoCalled": "",
    "whatIsIt": "",
    "signs": [],
    "whyItHappens": "",
    "whatToDo": [],
    "prevent": [],
}


@lru_cache(maxsize=1)
def _library() -> dict[str, dict]:
    with DISEASES_FILE.open(encoding="utf-8") as handle:
        return {
            slug: entry
            for slug, entry in json.load(handle).items()
            if not slug.startswith("_")
        }


def describe_disease(slug: str, confidence: float) -> dict:
    """One health prediction, with its full Uzbek guidance attached."""
    entry = _library().get(slug)
    if entry is None:
        # An unmapped label should still render rather than crash the scan.
        return {"slug": slug, "label": slug, "confidence": confidence, **EMPTY}

    return {
        "slug": slug,
        "label": entry["name"],
        "confidence": confidence,
        **{key: entry.get(key, default) for key, default in EMPTY.items()},
    }


def lookup(slug: str) -> dict | None:
    """The raw library entry, for the 'what to watch for' list."""
    return _library().get(slug)


def known_slugs() -> set[str]:
    return set(_library())
