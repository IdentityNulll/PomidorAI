"""Shared scan lookup, used by main.py and corrections.py."""

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from . import db, session as sess

NOT_FOUND = "Topilmadi"

# Corrections consulted per scan. The comparison is one matrix product, so
# this can grow large before it costs anything measurable.
CORRECTION_LIMIT = 5000


def owned_scan(scan_id: str, request: Request, database: Session) -> db.Scan:
    """The scan, if it belongs to the caller's session. 404 otherwise."""
    session_id = sess.read_session(request)
    if not session_id:
        raise HTTPException(status_code=404, detail=NOT_FOUND)

    scan = database.query(db.Scan).filter_by(id=scan_id, session_id=session_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return scan


def load_corrections(database: Session) -> list[tuple[str, bytes]]:
    """Every correction users have made, newest first.

    Deliberately not scoped to a session: a correction is knowledge about
    plants, not personal data, and the app should get better as it is used.
    """
    rows = (
        database.query(db.Correction)
        .order_by(db.Correction.created_at.desc())
        .limit(CORRECTION_LIMIT)
        .all()
    )
    return [(row.plant_id, row.embedding) for row in rows]
