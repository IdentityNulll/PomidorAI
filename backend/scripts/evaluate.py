"""Score the analyzer against the labelled photo sets.

Two sets, because they fail differently:

  * the owner's own garden photos, labelled by them (tests/data/garden_truth.json)
  * harvested produce from Wikimedia Commons

Point it at the directories and it prints per-photo results and a summary:

    python backend/scripts/evaluate.py --garden ~/Documents/pomidorai-test-images/newtests

Use this before and after any prompt change. Prompt edits that help one
photo routinely break two others, and only the totals show that.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TRUTH_FILE = ROOT / "tests" / "data" / "garden_truth.json"


def _shown(result, floor: float) -> str:
    plant = result["plant"]
    if plant["confidence"] < floor:
        return ""
    return plant["id"]


def run(directory: Path, truth: dict[str, str], label: str) -> tuple[int, int]:
    from app.analyzer import analyze
    from app.vision.thresholds import UNSURE_BELOW

    files = sorted(directory.glob("*.jpg"))
    correct = total = 0
    print(f"\n=== {label} ({len(files)} photos) ===")
    for index, path in enumerate(files, 1):
        expected = truth.get(str(index)) or truth.get(path.stem)
        result = analyze(str(path))
        got = _shown(result, UNSURE_BELOW)
        if expected is None:
            print(f"  {index:02d} {path.name[:28]:<30} -> {got or '(unnamed)'}")
            continue
        total += 1
        hit = got == expected
        correct += hit
        mark = "OK " if hit else "BAD"
        print(f"{mark} {index:02d} expected {expected:<14} -> {got or '(unnamed)':<14}"
              f"{result['plant']['confidence']:.2f}  view={result['view'] or '-'}")
    if total:
        print(f"  {label}: {correct}/{total}")
    return correct, total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--garden", type=Path, help="directory of the owner's labelled photos")
    parser.add_argument("--produce", type=Path, help="directory of harvested-produce photos")
    args = parser.parse_args()

    overall_correct = overall_total = 0

    if args.garden and args.garden.is_dir():
        truth = json.loads(TRUTH_FILE.read_text())["labels"]
        correct, total = run(args.garden, truth, "garden photos")
        overall_correct += correct
        overall_total += total

    if args.produce and args.produce.is_dir():
        manifest = args.produce / "manifest.json"
        truth = {}
        if manifest.exists():
            from app.vision import names

            by_name = {entry["commonName"]: entry["id"] for entry in names._plants().values()}
            for row in json.loads(manifest.read_text()):
                truth[row["slug"]] = by_name.get(row["expect"], row["expect"])
        correct, total = run(args.produce, truth, "harvested produce")
        overall_correct += correct
        overall_total += total

    if overall_total:
        print(f"\nTOTAL {overall_correct}/{overall_total} "
              f"({overall_correct / overall_total:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
