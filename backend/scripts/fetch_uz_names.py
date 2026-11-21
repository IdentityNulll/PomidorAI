"""Build the Uzbek species-name table from Wikidata.

The species model knows 7806 scientific names; Wikidata knows what many of
them are called in Uzbek, under CC0. Querying it once and committing the
result keeps the app fully offline at runtime.

    python backend/scripts/fetch_uz_names.py

Writes app/vision/data/uz_species.json:
    {"Cydonia oblonga": {"uz": "Behi", "desc": "..."}, ...}

Species without an Uzbek label fall back at runtime to the genus name, then
to the bare scientific name - handled in names.py, not here.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "app" / "vision" / "data" / "uz_species.json"
ENDPOINT = "https://query.wikidata.org/sparql"
UA = {"User-Agent": "PomidorAI-dev/1.0 (one-off dataset build; local use)"}
BATCH = 120

QUERY = """SELECT ?name ?uzLabel ?uzDesc ?ruLabel WHERE {
  VALUES ?name { %s }
  ?taxon wdt:P225 ?name .
  OPTIONAL { ?taxon rdfs:label ?uzLabel . FILTER(LANG(?uzLabel)="uz") }
  OPTIONAL { ?taxon schema:description ?uzDesc . FILTER(LANG(?uzDesc)="uz") }
  OPTIONAL { ?taxon rdfs:label ?ruLabel . FILTER(LANG(?ruLabel)="ru") }
}"""


def ask(names: list[str], attempt: int = 0) -> list[dict]:
    values = " ".join('"%s"' % n.replace('"', "") for n in names)
    url = f"{ENDPOINT}?format=json&query=" + urllib.parse.quote(QUERY % values)
    try:
        request = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.load(response)["results"]["bindings"]
    except Exception as exc:
        if attempt >= 3:
            print(f"  giving up on a batch: {exc}")
            return []
        wait = 15 * (attempt + 1)
        print(f"  retry in {wait}s ({exc})")
        time.sleep(wait)
        return ask(names, attempt + 1)


def species_names() -> list[str]:
    """Every scientific name the species model can emit."""
    from app.vision.plantnet import species_list

    return species_list()


def main() -> int:
    names = species_names()
    print(f"{len(names)} species to look up")

    table: dict[str, dict] = {}
    if OUT.exists():  # resume a partial run
        table = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"  resuming, {len(table)} already known")

    todo = [n for n in names if n not in table]
    for start in range(0, len(todo), BATCH):
        chunk = todo[start : start + BATCH]
        for row in ask(chunk):
            name = row["name"]["value"]
            entry = table.setdefault(name, {})
            if "uzLabel" in row:
                entry["uz"] = row["uzLabel"]["value"]
            if "uzDesc" in row:
                entry["desc"] = row["uzDesc"]["value"]
            if "ruLabel" in row:
                entry["ru"] = row["ruLabel"]["value"]
        # Mark the whole chunk as attempted so a resume does not redo it.
        for name in chunk:
            table.setdefault(name, {})

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(table, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
        done = start + len(chunk)
        hits = sum(1 for v in table.values() if v.get("uz"))
        print(f"  {done}/{len(todo)}  uzbek names so far: {hits}", flush=True)
        time.sleep(1.5)  # be polite to the public endpoint

    hits = sum(1 for v in table.values() if v.get("uz"))
    print(f"\n{hits}/{len(table)} have an Uzbek name -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
