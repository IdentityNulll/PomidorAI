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
| Vision   | PyTorch (CPU) + timm + transformers: PlantNet for species (7806), PlantVillage ViT for disease, CLIP for gating |
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
- No GPU, and no training step: all three models are pretrained

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

All analysis goes through one function - `analyze(image_path)` in
**`backend/app/analyzer.py`** - which is the only thing `main.py` calls. The
models live in `backend/app/vision/`. Everything runs locally on CPU.

| Model | Source | Job |
| ----- | ------ | --- |
| PlantNet mobilenetv4 | `PlantNet/mobilenetv4-conv-s-plantclef2024` (Apache-2.0) | **what plant is this** - 7806 species |
| CLIP ViT-B/32 | `laion/CLIP-ViT-B-32-laion2B-s34B-b79K` | two gates: "is this a plant at all" and "is this a close-up leaf" |
| PlantVillage ViT | `kimcomehome/plantvillage-vit-leaf-disease` | disease, for 14 crops, on leaf close-ups |

No training step. All three are pretrained and downloaded once
(`backend/scripts/fetch_models.py`), then run offline.

### Why three models

Neither specialist can say "I don't know". PlantNet returns a species for a
photo of a car; the PlantVillage model returns a disease for a photo of a
rose. CLIP supplies the two abstentions:

1. **plantness** - no plant in frame, stop and report nothing.
2. **leafiness** - not a close-up leaf, so cap any disease claim into the
   "not sure" band. The disease model was trained on single leaves against
   plain backgrounds and is unreliable on field and whole-plant shots.

On a close-up leaf the disease model may *also* correct the species, but only
when PlantNet is itself unsure. It has 14 classes and cannot abstain, so on a
beet leaf it confidently answers "Tomato" - letting that win turned a correct
"Lavlagi 0.86" into "Pomidor 0.69" during development.

### What the user sees, in three tiers

The species model knows 7806 plants; we do not have Uzbek agronomy advice for
all of them, and will not invent it.

1. **Curated crop** (19 in `data/plants.json`) - full Uzbek card: water,
   sun, soil, season, diseases, care tips.
2. **Known to Wikidata** (241 species) - correct Uzbek name, falling back to
   the genus's name, plus a short description where one exists. No advice.
3. **Neither** - the scientific name alone.

Uzbek names come from Wikidata (CC0), fetched once by
`backend/scripts/fetch_uz_names.py` into `app/vision/data/uz_species.json`
so runtime stays offline.

### Confidence is calibrated, and the threshold is measured

With 7806 classes the probability mass is spread far thinner than with the
old 8-class model - a top-1 of 0.42 is about 3000x above chance. Measured on
1143 labelled photos:

| threshold | names a plant | of those, correct |
| --------- | ------------- | ----------------- |
| 0.50      | 20%           | 75%               |
| **0.30**  | **33%**       | **67%**           |
| 0.20      | 45%           | 61%               |

0.50 was inherited from the 8-class model and left this one mute on photos
where it knew the answer. The app uses **0.30**
(`backend/app/vision/thresholds.py`, mirrored in
`frontend/src/lib/confidence.ts`). The percentage is always shown next to the
name, and the disclaimer is permanent.

### Measured on 24 real garden photos

Taken on an Uzbek phone in November - peppers, autumn foliage, weeds, herbs,
roses - i.e. mostly *not* the eight crops the old model knew.

| | old 8-crop model | now |
| --- | --- | --- |
| named a plant | 20 of 24 | 10 of 24 |
| named it correctly | ~2 | 10 |

The old model force-fitted everything into eight crops: pepper plants came
back "Pomidor", weeds "Kartoshka", coriander "Uzum". Now it correctly names
Kashnich (coriander), Lavlagi (beet), Behi (quince), Shivit (dill),
Xrizantema and Itburun (rose) - and says nothing on the other 14 rather than
guessing.

### What it still cannot do

- **Half the photos get no name.** Autumn foliage and distant whole-plant
  shots are genuinely hard; the model abstains instead of guessing. Close-ups
  of leaves or flowers work much better.
- **Disease only for 14 crops** (tomato, potato, apple, grape, pepper, maize,
  cherry, peach, strawberry, squash, orange, soybean, blueberry, raspberry)
  and only on **close-up single-leaf photos**. Everything else is reported as
  unsure by design.
- **Only 19 plants have Uzbek growing advice**, and 241 of 7806 have an Uzbek
  name at all. The rest show a Latin binomial.
- PlantVillage models degrade on real field photography versus their training
  set. Treat output as a prompt to look closer - which is what the permanent
  disclaimer says.

### Swapping in different models

The seam is unchanged. `analyze()` takes an absolute path to a normalised
JPEG (RGB, <=1280 px, EXIF stripped) and returns:

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

- Confidences must be **calibrated probabilities in 0.0-1.0**, not logits.
- `commonName` may be empty; the UI then shows `scientificName` as the heading.
- `plant.id` matches `plants.json` when curated, `"wild"` for an uncurated
  species, `"unknown"` when the photo is not a plant.
- Override the checkpoints with `POMIDORAI_SPECIES_MODEL`,
  `POMIDORAI_DISEASE_MODEL`, `POMIDORAI_CLIP_MODEL`.
- Inference runs in a threadpool so it does not block the event loop.

### Placeholder content

`backend/app/data/plants.json` (19 crops) and the Uzbek disease names in
`backend/app/vision/labels.py` are **machine-written and have not been
reviewed by an agronomist.** Verify before the app gives real advice - see
`backend/app/data/README.md`. The Wikidata names are CC0 community data and
carry the same caveat.

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
│   │   │   ├── plantnet.py    # species: 7806 plants
│   │   │   ├── gates.py       # CLIP: is-a-plant / is-a-leaf
│   │   │   ├── disease.py     # PlantVillage ViT + weak CLIP fallback
│   │   │   ├── names.py       # scientific name -> Uzbek, three tiers
│   │   │   ├── thresholds.py  # the measured confidence floor
│   │   │   ├── models.py      # lazy, cached CLIP + disease loading
│   │   │   ├── labels.py      # prompts, English -> Uzbek disease names
│   │   │   └── data/          # uz_species.json (Wikidata, CC0)
│   │   ├── images.py          # upload validation, resize, EXIF strip
│   │   ├── session.py         # signed anonymous session cookie
│   │   ├── db.py              # SQLAlchemy engine + Scan model
│   │   ├── models.py          # Pydantic schemas
│   │   └── data/
│   │       ├── plants.json    # placeholder content - needs agronomist review
│   │       └── README.md
│   ├── scripts/               # fetch_models.py, fetch_uz_names.py
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
