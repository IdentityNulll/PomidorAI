"""The correction loop: the crop list, and recording "it is actually this".

Split out of main.py to keep both files readable. See vision/memory.py for
how a stored correction is used on later scans.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from . import db, models
from .images import resolve_owned_file
from .scans import owned_scan
from .vision import memory as vision_memory
from .vision import names as vision_names

logger = logging.getLogger(__name__)

router = APIRouter()


def _embed_scan(path) -> bytes:
    from PIL import Image

    with Image.open(path) as handle:
        return vision_memory.encode(handle.convert("RGB"))


@router.get("/api/plants", response_model=list[models.PlantOption])
def list_plants():
    """Crops the user can choose from when correcting a result."""
    entries = sorted(
        vision_names._plants().values(), key=lambda entry: entry["commonName"]
    )
    return [
        models.PlantOption(
            id=entry["id"],
            commonName=entry["commonName"],
            scientificName=entry["scientificName"],
        )
        for entry in entries
    ]


@router.post("/api/scans/{scan_id}/correct", response_model=models.ScanDetail)
async def correct_scan(
    scan_id: str,
    body: models.CorrectionRequest,
    request: Request,
    database: Session = Depends(db.get_db),
):
    """Record that a scan was wrong, and what it really is.

    The photo's CLIP embedding is stored with the correct label, so a
    similar photo is recognised next time with no retraining.
    """
    scan = owned_scan(scan_id, request, database)

    curated = vision_names.by_plant_id(body.plantId)
    if not curated:
        raise HTTPException(status_code=400, detail="Noma'lum o'simlik")

    result = json.loads(scan.result)
    try:
        embedding = await run_in_threadpool(
            _embed_scan, resolve_owned_file(scan.image_path)
        )
    except Exception:
        logger.exception("could not embed scan for correction")
        raise HTTPException(status_code=500, detail="Saqlab bo'lmadi")

    database.add(
        db.Correction(
            id=db.new_id(),
            plant_id=body.plantId,
            embedding=embedding,
            predicted_id=result["plant"].get("id"),
        )
    )

    # Rewrite the stored scan so history agrees with the correction.
    result["plant"] = {
        "id": curated["id"],
        "commonName": curated["commonName"],
        "scientificName": curated["scientificName"],
        "confidence": 1.0,
    }
    result["info"] = {key: curated[key] for key in result["info"]}
    scan.result = json.dumps(result, ensure_ascii=False)
    database.commit()

    return models.ScanDetail(
        id=scan.id,
        plant=result["plant"],
        health=result["health"],
        info=result["info"],
        view=result.get("view", ""),
        createdAt=scan.created_at,
    )
