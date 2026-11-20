"""Download a training set of crop photos from Wikimedia Commons.

Commons images are CC-licensed or public domain. We only need a few hundred
per class: the classifier trained on top of these is a linear probe over
frozen CLIP features, not a network trained from scratch.

    python backend/scripts/fetch_dataset.py --per-class 260

Images land in backend/data/dataset/<class>/ (gitignored). Re-running skips
what is already there, so an interrupted download can just be repeated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "dataset"
API = "https://commons.wikimedia.org/w/api.php"
UA = "PomidorAI-dev/1.0 (local model training; contact: local user)"

# Search terms per class. Several per crop, because one term alone returns a
# narrow slice (all fruit, or all field shots) and the classifier then fails
# on the views it never saw.
QUERIES: dict[str, list[str]] = {
    "tomato": [
        "Solanum lycopersicum plant", "tomato plant leaves", "tomato fruit",
        "tomato plant greenhouse", "tomato seedling",
    ],
    "cotton": [
        "Gossypium plant", "cotton boll", "cotton field",
        "cotton plant leaves", "Gossypium hirsutum flower",
    ],
    "grape": [
        "Vitis vinifera leaves", "grape bunch", "vineyard vines",
        "grape vine plant", "grapes on vine",
    ],
    "apple": [
        "Malus domestica tree", "apple fruit", "apple tree leaves",
        "apple orchard", "apple blossom tree",
    ],
    "wheat": [
        "Triticum aestivum", "wheat field", "wheat ear",
        "wheat plant leaves", "wheat harvest crop",
    ],
    "pomegranate": [
        "Punica granatum tree", "pomegranate fruit", "pomegranate leaves",
        "pomegranate flower", "pomegranate orchard",
    ],
    "apricot": [
        "Prunus armeniaca tree", "apricot fruit", "apricot tree leaves",
        "apricot blossom", "apricot orchard",
    ],
    "potato": [
        "Solanum tuberosum plant", "potato plant leaves", "potato tuber",
        "potato field crop", "potato flower plant",
    ],
    # Negatives. Deliberately includes OTHER crops and plants: the model must
    # reject a maize leaf or a rose, not just reject cats.
    "__not_a_crop__": [
        "maize plant", "sunflower plant", "cucumber plant", "bell pepper plant",
        "rose flower", "oak tree", "houseplant pot", "cactus",
        "domestic cat", "dog", "car", "office building",
        "cooked meal plate", "person portrait", "grass lawn", "soil ground",
    ],
}


def api_get(params: dict) -> dict:
    url = f"{API}?{urllib.parse.urlencode({**params, 'format': 'json'})}"
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def search(term: str, limit: int) -> list[str]:
    """Thumbnail URLs for files matching a term."""
    try:
        data = api_get({
            "action": "query", "generator": "search", "gsrnamespace": 6,
            "gsrlimit": min(limit, 500), "gsrsearch": term,
            "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 512,
        })
    except Exception as exc:
        print(f"    search failed for {term!r}: {exc}")
        return []

    urls = []
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        # Commons search also returns PDFs, SVGs and video.
        if info.get("mime") in {"image/jpeg", "image/png"} and info.get("thumburl"):
            urls.append(info["thumburl"])
    return urls


def download(url: str, target_dir: Path) -> bool:
    name = hashlib.sha1(url.encode()).hexdigest()[:16] + ".jpg"
    path = target_dir / name
    if path.exists():
        return False
    try:
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
        if len(payload) < 2000:  # placeholder or error page
            return False
        path.write_bytes(payload)
        return True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-class", type=int, default=260)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    for label, terms in QUERIES.items():
        target_dir = OUT / label
        target_dir.mkdir(parents=True, exist_ok=True)
        existing = len(list(target_dir.glob("*.jpg")))
        if existing >= args.per_class:
            print(f"{label}: already have {existing}, skipping")
            continue

        per_term = max(8, args.per_class // len(terms) + 12)
        urls: list[str] = []
        for term in terms:
            urls.extend(search(term, per_term))

        # Dedupe while keeping the interleaved order across terms.
        seen = set()
        unique = [u for u in urls if not (u in seen or seen.add(u))]
        need = args.per_class - existing

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            got = sum(pool.map(lambda u: download(u, target_dir), unique[: need * 2]))

        print(f"{label}: +{got} (total {len(list(target_dir.glob('*.jpg')))})")

    print(f"\ndataset at {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
