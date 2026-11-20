# PomidorAI

Mobile-first web app for identifying crops and garden plants from a photo and
flagging whether they look diseased. Built for farmers and gardeners in
Uzbekistan; the entire UI is in Uzbek (Latin script).

Identification and disease detection run on **real models, locally on CPU** —
no GPU, no external API, nothing leaves the machine. Read
[How the analysis works](#how-the-analysis-works) before trusting it: the
accuracy limits are real and specific.

---

## Stack

| Layer    | Choice                                                                   |
| -------- | ------------------------------------------------------------------------ |
| Backend  | Python, FastAPI, SQLite (SQLAlchemy), Pillow                             |
| Vision   | PyTorch (CPU) + transformers: CLIP for species, a PlantVillage ViT for disease |
| Frontend | React 18 + Vite + TypeScript, Tailwind CSS, lucide-react, self-hosted Inter |
| Tests    | pytest (backend), Playwright (mobile UI)                                 |

Everything runs locally and offline. There are no external API calls and no CDN
assets — the Inter font ships from `@fontsource` and is bundled at build time.
The model weights are downloaded once, then cached; after that you can set
`HF_HUB_OFFLINE=1` and the app still works.

## Requirements

- Python 3.10+
- Node.js 18+
- ~1 GB disk for the model weights, ~2 GB RAM while running

## Running

### Development

```bash
./dev.sh
```

FastAPI runs on `:8000` with reload; Vite runs on `:5173` and proxies `/api` to
it. **Open <http://localhost:5173>.** The script creates `backend/venv` and
installs dependencies on first run.

### Production

```bash
./start.sh
```

Builds the frontend into `backend/static/` and serves the API *and* the site
from a single FastAPI process on `0.0.0.0:8000`. The script prints your LAN IP
so a phone on the same Wi-Fi can open `http://<your-ip>:8000`.

### Tests

```bash
cd backend && ./venv/bin/python -m pytest
```

The default suite stubs the models so it runs in about a second. To exercise
the real weights:

```bash
cd backend && POMIDORAI_MODEL_TESTS=1 ./venv/bin/python -m pytest tests/test_models.py
```

```bash
cd frontend && npm run build && npm run lint
```

```bash
# Mobile UI tests - needs the production server running (./start.sh)
cd frontend && npx playwright test
```

Playwright covers iPhone 13 and Pixel 7 profiles: the full scan → result →
history → detail → delete flow, low-confidence / error / offline / empty
states, and assertions that nothing scrolls horizontally, every tap target is
at least 44×44 px, and content text is at least 16 px. Screenshots land in
`frontend/screenshots/`.

> Both profiles currently run on Chromium. Playwright's WebKit build needs
> system packages this machine lacks; install them with
> `sudo npx playwright install-deps` and drop the `defaultBrowserType` override
> in `playwright.config.ts` to test the real iOS engine.

## How sessions work

There are no accounts. On the first `POST /api/analyze`, the server mints a
random session id and returns it in a cookie:

- name `pomidorai_session`, **httpOnly**, `SameSite=Lax`, `Max-Age` 2 years
- the value is **signed** with `itsdangerous`, so a client cannot forge or
  guess another session's id — a tampered cookie is treated as no cookie

Every scan row stores this session id. Listing, reading, image access and
deletion all filter on it, so one device can never see or delete another's
scans. History is capped at **200 scans per session**; older ones are deleted
along with their files.

The signing secret comes from `$POMIDORAI_SECRET`, or is generated once and
stored in `backend/data/secret.key` (mode 600). **Set `POMIDORAI_SECRET`
explicitly in production** — losing the key invalidates every existing session.

## Privacy and upload safety

- The client's declared MIME type and filename are never trusted; the format is
  taken from the decoded pixel data and must be JPEG, PNG or WebP.
- Max upload 8 MB; images are re-encoded to JPEG with the longest side ≤1280 px.
- Re-encoding **strips EXIF**, which on phone photos routinely contains GPS
  coordinates. There is a test asserting the stored files carry no EXIF.
- File reads are resolved against `backend/data/uploads/` and refuse anything
  outside it.

## How the analysis works

All analysis still goes through one function — `analyze(image_path)` in
**`backend/app/analyzer.py`** — which is the only thing `main.py` calls. The
models live in `backend/app/vision/`.

Two models, each used only where it is actually good:

| Model | Repo | Used for |
| ----- | ---- | -------- |
| CLIP ViT-B/32 | `laion/CLIP-ViT-B-32-laion2B-s34B-b79K` | frozen feature extractor, plus the "is this a close-up leaf" gate |
| Species head | `app/vision/weights/species_head.npz` (trained here) | species on whole-plant / fruit / field photos, and rejecting non-crops |
| PlantVillage ViT | `kimcomehome/plantvillage-vit-leaf-disease` | disease, and species on close-up leaves |

### Routing

Species comes from a **linear head trained on real photographs** (see
[Training the species head](#training-the-species-head)), blended with the
older zero-shot prompts. Both score the photo against the eight crops in
`plants.json` *plus* a **"not a crop" class**. That extra class matters: a
softmax over eight crops has nowhere else to put its mass, so without it a
photo of a cat comes back as a confident crop. With it, the app says
unidentified.

Then the photo is classified as leaf-like or not, because the disease model
was trained on single leaves against plain backgrounds and is unreliable
anywhere else:

- **Not leaf-like** (whole plant, fruit, field) → the species head decides.
  Any disease output is capped below the UI's 0.50 threshold, so the app says
  "not sure" instead of diagnosing from a photo the model cannot read.
- **Leaf-like** → the PlantVillage model decides the species, because CLIP
  features are weak at fine-grained leaf shapes (most broad green leaves read
  as cotton). If neither model is confident, the result is reported as unsure
  rather than guessed.

Health predictions are never more confident than the species they assume.

### Measured accuracy

Species identification, on **280 held-out images** the trained head never
saw (9 classes: the eight crops plus "not a crop"). Images are degraded to
each size and re-compressed, imitating a phone upload over slow mobile data:

| resolution | zero-shot prompts | trained head | production (blended) |
| ---------- | ----------------- | ------------ | -------------------- |
| full       | 66.4%             | 78.2%        | **79.3%**            |
| 640 px     | 67.1%             | 78.9%        | **78.9%**            |
| 320 px     | 66.4%             | 80.0%        | **78.9%**            |
| 160 px     | 62.5%             | 73.9%        | **73.2%**            |
| 96 px      | 53.6%             | 64.6%        | **62.9%**            |

Two things worth reading off this table:

- **Low resolution barely matters until it is extreme.** 320 px scores the
  same as full resolution, and 160 px (73.2%) still beats the old zero-shot
  prompts at *full* resolution (66.4%). CLIP resizes everything to 224x224
  anyway, so there is little left to lose until the image drops below that.
- **The blend only clearly helps at full resolution.** Below it, head-only is
  within a point or two either way. At n=280 that is inside the noise
  (standard error ~2.4 points), so do not read the 320/160 rows as the blend
  hurting. It is kept because it fixes a real failure mode (below).

Per-class recall, because a single average hides a lot:

| class | recall | | class | recall |
| ----- | ------ | - | ----- | ------ |
| wheat | 90.0% | | apple | 74.1% |
| not-a-crop | 87.5% | | grape | 73.1% |
| cotton | 82.8% | | apricot | 72.2% |
| pomegranate | 81.8% | | potato | 58.3% |
| tomato | 74.1% | | | |

Potato is the weakest class and is mostly lost to cotton. Apple and apricot
trade with each other, which is unsurprising for two similar orchard trees.

### Why the head is blended with the prompts

The two methods fail differently, so `identify()` combines them with a
geometric blend (`BLEND_ALPHA = 0.75`, favouring the head).

The head alone read a perfectly ordinary whole-plant tomato photo as
"not a crop" at 0.70, where the prompts had it at 0.99. Blended, it comes
back as tomato and the app shows a name again.

The blend weight was chosen on one half of the held-out split and confirmed
on the other half, which had no part in choosing it: **0.793 blended vs
0.779 head-only vs 0.657 zero-shot**. Tuning a hyperparameter on the same
data you then quote is how a benchmark ends up lying.

### An earlier benchmark that turned out to be contaminated

An earlier nine-photo end-to-end check is no longer an accuracy claim: three
of those photos (potato, wheat, cat) were pulled into the training set by
`fetch_dataset.py`, which searches Commons with overlapping terms. Verified
by comparing the URL hashes the fetcher names files with, not by assuming.

On the six genuinely held-out photos the full pipeline gives 4 correct, 1
unsure, 1 wrong. Treat that run as a smoke test of the routing; the 280-image
split above is the real number.

### What it cannot do

- **Only the four crops tomato, potato, apple and grape get real disease
  detection.** Cotton, wheat, pomegranate and apricot fall back to a CLIP
  healthy-vs-diseased prompt comparison, which is a weak signal and is
  deliberately capped into the "unsure" band.
- Disease detection needs a **close-up of a single leaf**. Field and
  whole-plant shots will not produce a diagnosis by design.
- The eight crops are a closed set. Anything else should come back
  unidentified — that is what the distractors are for.
- PlantVillage models are known to degrade on real field photography compared
  to their training set. Treat output as a prompt to look closer, which is
  exactly what the app's permanent disclaimer says.

### Training the species head

Species identification does not rely on hand-written prompts any more. A
**linear probe** over frozen CLIP features is trained on real photographs:

```bash
python backend/scripts/fetch_dataset.py --per-class 260   # ~1400 CC images from Wikimedia Commons
python backend/scripts/train_head.py                      # minutes on CPU
python backend/scripts/evaluate_head.py                   # accuracy vs zero-shot, by resolution
```

CLIP stays frozen; only a softmax layer on top of its embeddings is fitted.
That is why this trains on a laptop CPU in minutes instead of needing a GPU
for days — and why ~1400 images is enough, where training a network from
scratch would need orders of magnitude more.

The dataset lands in `backend/data/dataset/` (gitignored). The trained head is
`backend/app/vision/weights/species_head.npz`, a few hundred KB, and **is**
committed so a fresh checkout works without retraining. If the file is absent
the app silently falls back to the old zero-shot prompts.

**Low resolution is trained for, not hoped for.** Every training image is also
embedded at 640 px, 320 px and 160 px with JPEG quality dropped to match, so
the head learns the degraded features a phone photo actually arrives with over
slow mobile data. `evaluate_head.py` reports accuracy per resolution.

The negative class matters as much as the crops: it contains other plants and
crops (maize, sunflower, cucumber, pepper, roses, oaks) and not just obviously
non-plant photos, so the model learns to reject *a plant that is not one of
our eight* rather than merely rejecting cats.

### Swapping in different models

The seam is unchanged. `analyze()` takes an absolute path to a normalised JPEG
(RGB, ≤1280 px, EXIF stripped) and returns:

```python
{
  "plant":  {"id": str, "commonName": str, "scientificName": str, "confidence": float},
  "health": {"predictions": [{"label": str, "confidence": float}]},   # up to 3
  "info": {
    "description": str, "howItGrows": str, "water": str, "sunlight": str,
    "soil": str, "season": str,
    "commonDiseases": [str], "careTips": [str],
  },
}
```

- Confidences must be **calibrated probabilities in 0.0–1.0**, not logits. The
  UI hides the plant name and shows "Ishonchim komil emas…" below **0.50** and
  applies the same rule to health.
- `plant.id` must match an id in `plants.json`; `info` is looked up from there.
- `health.predictions` should include a healthy class labelled `Sog'lom`.
- Point at different weights without touching code via `POMIDORAI_CLIP_MODEL`
  and `POMIDORAI_DISEASE_MODEL`.
- Inference runs in a threadpool (`run_in_threadpool`) so it does not block the
  event loop. If it gets much slower, move it to a worker — the API contract
  does not change.

### ⚠️ Placeholder content

`backend/app/data/plants.json` holds 8 plants (tomato, cotton, grape, apple,
wheat, pomegranate, apricot, potato). **All of its Uzbek text is
machine-written and has not been reviewed by an agronomist**, and so are the
Uzbek disease names in `backend/app/vision/labels.py`. Both must be verified
before the app gives real advice — see `backend/app/data/README.md`.

## API

All endpoints are under `/api`. Identity comes from the session cookie
described above; it is set automatically by the first `POST /api/analyze`.

### `GET /api/health`

```json
{ "status": "ok" }
```

### `POST /api/analyze`

`multipart/form-data` with one field, `image`.

Validates and normalises the upload, runs the analyzer, stores the scan, and
returns the full record. Sets the session cookie if the caller has none.

- `200` — a `ScanDetail` (see below)
- `400` — not a decodable JPEG/PNG/WebP
- `413` — larger than 8 MB
- `422` — no `image` field

### `GET /api/scans?cursor=&limit=`

Paginated list, newest first. `limit` defaults to 20 and is clamped to 50.
Pass the returned `cursor` back to get the next page; `cursor` is `null` on the
last page. Returns `{"scans": [], "cursor": null}` when there is no session.

```json
{
  "scans": [
    {
      "id": "…",
      "plant": { "id": "tomato", "commonName": "Pomidor",
                 "scientificName": "Solanum lycopersicum", "confidence": 0.93 },
      "health": { "predictions": [{ "label": "Sog'lom", "confidence": 0.81 }] },
      "createdAt": "2026-11-20T14:49:02"
    }
  ],
  "cursor": "eyJ…"
}
```

### `GET /api/scans/{id}`

One scan including the `info` card. `404` if it does not exist **or** belongs to
another session.

```json
{
  "id": "…",
  "plant": { "...": "as above" },
  "health": { "...": "as above" },
  "info": {
    "description": "…", "howItGrows": "…", "water": "…", "sunlight": "…",
    "soil": "…", "season": "…",
    "commonDiseases": ["Fitoftoroz"], "careTips": ["…"]
  },
  "createdAt": "2026-11-20T14:49:02"
}
```

### `GET /api/scans/{id}/image` · `GET /api/scans/{id}/thumb`

The stored JPEG (≤1280 px) and its thumbnail (≤320 px). Served only to the
owning session; `404` otherwise.

### `DELETE /api/scans/{id}` · `DELETE /api/scans`

Delete one scan, or every scan for the session. Removes the database rows and
the files on disk. Both return `{"status": "deleted"}`.

Timestamps are naive UTC ISO-8601.

## Project layout

```
pomidorAI/
├── dev.sh                     # backend reload + Vite dev server
├── start.sh                   # build frontend, serve everything on :8000
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py            # routes
│   │   ├── analyzer.py        # THE SEAM - routing between the two models
│   │   ├── vision/            # the models themselves
│   │   │   ├── models.py      # lazy, cached loading
│   │   │   ├── species.py     # CLIP zero-shot + leaf / distractor gates
│   │   │   ├── disease.py     # PlantVillage ViT + weak CLIP fallback
│   │   │   └── labels.py      # prompts and English -> Uzbek disease names
│   │   ├── images.py          # upload validation, resize, EXIF strip
│   │   ├── session.py         # signed anonymous session cookie
│   │   ├── db.py              # SQLAlchemy engine + Scan model
│   │   ├── models.py          # Pydantic schemas
│   │   └── data/
│   │       ├── plants.json    # placeholder content - needs agronomist review
│   │       └── README.md
│   ├── scripts/fetch_models.py  # one-time weight download
│   ├── tests/
│   └── data/                  # gitignored: uploads/, pomidorai.db, secret.key
└── frontend/
    ├── index.html
    ├── public/                # manifest, service worker, icons
    ├── e2e/                   # Playwright mobile tests
    └── src/
        ├── App.tsx
        ├── types.ts           # mirrors the Pydantic models
        ├── i18n/uz.ts         # every UI string, in one file
        ├── lib/               # api.ts, image.ts (decode/rotate/resize)
        ├── hooks/
        └── components/
```

## PWA

`public/manifest.webmanifest` plus a minimal service worker (`public/sw.js`)
make the app installable to the home screen and let the shell load offline.
`/api` is never cached — scanning needs the server, so the UI shows an Uzbek
offline message instead of failing silently.
