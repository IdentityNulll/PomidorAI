# PomidorAI

Mobile-first web app for identifying crops and garden plants from a photo and
flagging whether they look diseased. Built for farmers and gardeners in
Uzbekistan; the entire UI is in Uzbek (Latin script).

**The AI is a mock.** Plant identification and disease detection are not
implemented yet — `backend/app/analyzer.py` returns randomised placeholder
results. Everything around it (upload, validation, storage, history, UI) is
real and finished. See [Replacing the mock](#replacing-the-mock-with-real-models).

---

## Stack

| Layer    | Choice                                                                   |
| -------- | ------------------------------------------------------------------------ |
| Backend  | Python, FastAPI, SQLite (SQLAlchemy), Pillow                             |
| Frontend | React 18 + Vite + TypeScript, Tailwind CSS, lucide-react, self-hosted Inter |
| Tests    | pytest (backend), Playwright (mobile UI)                                 |

Everything runs locally and offline. There are no external API calls and no CDN
assets — the Inter font ships from `@fontsource` and is bundled at build time.

## Requirements

- Python 3.10+
- Node.js 18+

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

## Replacing the mock with real models

Edit **`backend/app/analyzer.py`** and nothing else.

It exposes exactly one function:

```python
def analyze(image_path: str) -> dict
```

`image_path` is an absolute path to a normalised JPEG (RGB, ≤1280 px, EXIF
already stripped). Return this shape:

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

Notes for whoever wires up the real models:

- Confidences are **0.0–1.0 and must be calibrated probabilities**, not raw
  logits. The UI hides the plant name and shows "Ishonchim komil emas…" below
  **0.50**, and applies the same rule to the health result.
- `health.predictions` should include a healthy class labelled `Sog'lom`.
- The call is synchronous and runs inside the request. If inference gets slow,
  move it to a worker — the API contract does not need to change.
- `info` is reference content keyed to the predicted plant. Today it is read
  from `backend/app/data/plants.json`.

### ⚠️ Placeholder content

`backend/app/data/plants.json` holds 8 plants (tomato, cotton, grape, apple,
wheat, pomegranate, apricot, potato). **All of its Uzbek text is
machine-written and has not been reviewed by an agronomist.** It must be
verified before the app gives real advice — see
`backend/app/data/README.md`.

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
│   │   ├── analyzer.py        # THE MOCK - the only file to change for real models
│   │   ├── images.py          # upload validation, resize, EXIF strip
│   │   ├── session.py         # signed anonymous session cookie
│   │   ├── db.py              # SQLAlchemy engine + Scan model
│   │   ├── models.py          # Pydantic schemas
│   │   └── data/
│   │       ├── plants.json    # placeholder content - needs agronomist review
│   │       └── README.md
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
