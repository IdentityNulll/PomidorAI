"""Download the vision model weights into the local Hugging Face cache.

Run once (dev.sh and start.sh do it for you). After this the app works fully
offline; set HF_HUB_OFFLINE=1 to prove it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from huggingface_hub import snapshot_download  # noqa: E402

from app.vision.models import CLIP_MODEL, DISEASE_MODEL  # noqa: E402

TARGETS = [
    (CLIP_MODEL, ["*.json", "*.txt", "model.safetensors"]),
    (DISEASE_MODEL, ["*.json", "model.safetensors"]),
]


def main() -> int:
    for repo, patterns in TARGETS:
        print(f"==> {repo}")
        snapshot_download(repo, allow_patterns=patterns)
    print("models cached")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
