"""PomidorAI FastAPI application."""

import base64
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from . import db, models, session as sess
from .analyzer import analyze
from .images import ERR_DECODE, remove_files, resolve_owned_file, save_upload

HISTORY_LIMIT = 200
STATIC_DIR = Path(__file__).parent.parent / "static"
NOT_FOUND = "Topilmadi"


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="PomidorAI", lifespan=lifespan)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _encode_cursor(scan: db.Scan) -> str:
    raw = f"{scan.created_at.isoformat()}|{scan.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        timestamp, scan_id = raw.split("|", 1)
        return datetime.fromisoformat(timestamp), scan_id
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Noto'g'ri cursor")


def _owned_scan(scan_id: str, request: Request, database: Session) -> db.Scan:
    session_id = sess.read_session(request)
    if not session_id:
        raise HTTPException(status_code=404, detail=NOT_FOUND)

    scan = database.query(db.Scan).filter_by(id=scan_id, session_id=session_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return scan


def _enforce_history_cap(session_id: str, database: Session) -> None:
    """Delete the oldest scans beyond HISTORY_LIMIT for this session."""
    stale = (
        database.query(db.Scan)
        .filter_by(session_id=session_id)
        .order_by(db.Scan.created_at.desc(), db.Scan.id.desc())
        .offset(HISTORY_LIMIT)
        .all()
    )
    for scan in stale:
        remove_files(scan.image_path, scan.thumbnail_path)
        database.delete(scan)


@app.get("/api/health", response_model=models.HealthResponse)
def health():
    return models.HealthResponse(status="ok")


@app.post("/api/analyze", response_model=models.ScanDetail)
async def analyze_endpoint(
    request: Request,
    response: Response,
    image: UploadFile = File(...),
    database: Session = Depends(db.get_db),
):
    session_id = sess.ensure_session(request, response)
    image_path, thumb_path = await save_upload(image)

    try:
        result = analyze(str(image_path))
    except Exception:
        remove_files(str(image_path), str(thumb_path))
        raise HTTPException(status_code=500, detail="Tahlil qilib bo'lmadi")

    scan = db.Scan(
        id=db.new_id(),
        session_id=session_id,
        image_path=str(image_path),
        thumbnail_path=str(thumb_path),
        result=json.dumps(result, ensure_ascii=False),
        created_at=_now(),
    )
    database.add(scan)
    database.flush()
    _enforce_history_cap(session_id, database)
    database.commit()
    database.refresh(scan)

    return models.ScanDetail(
        id=scan.id,
        plant=result["plant"],
        health=result["health"],
        info=result["info"],
        createdAt=scan.created_at,
    )


@app.get("/api/scans", response_model=models.ScanListResponse)
def list_scans(
    request: Request,
    cursor: str | None = None,
    limit: int = 20,
    database: Session = Depends(db.get_db),
):
    session_id = sess.read_session(request)
    if not session_id:
        return models.ScanListResponse(scans=[], cursor=None)

    limit = max(1, min(limit, 50))
    query = database.query(db.Scan).filter_by(session_id=session_id)

    if cursor:
        after_ts, after_id = _decode_cursor(cursor)
        query = query.filter(
            or_(
                db.Scan.created_at < after_ts,
                and_(db.Scan.created_at == after_ts, db.Scan.id < after_id),
            )
        )

    rows = (
        query.order_by(db.Scan.created_at.desc(), db.Scan.id.desc())
        .limit(limit + 1)
        .all()
    )

    next_cursor = _encode_cursor(rows[limit - 1]) if len(rows) > limit else None
    rows = rows[:limit]

    scans = []
    for row in rows:
        result = json.loads(row.result)
        scans.append(
            models.Scan(
                id=row.id,
                plant=result["plant"],
                health=result["health"],
                createdAt=row.created_at,
            )
        )

    return models.ScanListResponse(scans=scans, cursor=next_cursor)


@app.get("/api/scans/{scan_id}", response_model=models.ScanDetail)
def get_scan(scan_id: str, request: Request, database: Session = Depends(db.get_db)):
    scan = _owned_scan(scan_id, request, database)
    result = json.loads(scan.result)
    return models.ScanDetail(
        id=scan.id,
        plant=result["plant"],
        health=result["health"],
        info=result["info"],
        createdAt=scan.created_at,
    )


@app.get("/api/scans/{scan_id}/image")
def get_scan_image(scan_id: str, request: Request, database: Session = Depends(db.get_db)):
    scan = _owned_scan(scan_id, request, database)
    return FileResponse(resolve_owned_file(scan.image_path), media_type="image/jpeg")


@app.get("/api/scans/{scan_id}/thumb")
def get_scan_thumb(scan_id: str, request: Request, database: Session = Depends(db.get_db)):
    scan = _owned_scan(scan_id, request, database)
    return FileResponse(resolve_owned_file(scan.thumbnail_path), media_type="image/jpeg")


@app.delete("/api/scans/{scan_id}")
def delete_scan(scan_id: str, request: Request, database: Session = Depends(db.get_db)):
    scan = _owned_scan(scan_id, request, database)
    remove_files(scan.image_path, scan.thumbnail_path)
    database.delete(scan)
    database.commit()
    return {"status": "deleted"}


@app.delete("/api/scans")
def delete_all_scans(request: Request, database: Session = Depends(db.get_db)):
    session_id = sess.read_session(request)
    if not session_id:
        return {"status": "deleted"}

    for scan in database.query(db.Scan).filter_by(session_id=session_id).all():
        remove_files(scan.image_path, scan.thumbnail_path)
        database.delete(scan)
    database.commit()
    return {"status": "deleted"}


# Production: serve the built frontend from the same process. Registered last so
# the /api routes above always win.
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
