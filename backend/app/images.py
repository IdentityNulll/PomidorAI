"""Server-side upload validation and image normalisation."""

import uuid
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 8 * 1024 * 1024
MAX_SIDE = 1280
THUMB_SIDE = 320
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

ERR_TYPE = "Rasm turi mos emas. JPEG, PNG yoki WebP yuboring."
ERR_LARGE = "Rasm hajmi juda katta. Eng ko'pi 8 MB."
ERR_DECODE = "Rasmni o'qib bo'lmadi. Boshqa rasm bilan urinib ko'ring."


async def save_upload(file: UploadFile) -> tuple[Path, Path]:
    """Validate, normalise and store an upload. Returns (image, thumbnail) paths.

    The client's declared content type and filename are not trusted: the format
    is taken from the decoded pixel data. Re-encoding also drops EXIF, which can
    carry GPS coordinates.
    """
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=ERR_LARGE)
    if not content:
        raise HTTPException(status_code=400, detail=ERR_DECODE)

    try:
        probe = Image.open(BytesIO(content))
        detected = (probe.format or "").upper()
        if detected not in ALLOWED_FORMATS:
            raise HTTPException(status_code=400, detail=ERR_TYPE)
        probe.verify()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail=ERR_DECODE)

    try:
        img = Image.open(BytesIO(content))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail=ERR_DECODE)

    image_id = uuid.uuid4().hex
    image_path = UPLOAD_DIR / f"{image_id}.jpg"
    thumb_path = UPLOAD_DIR / f"{image_id}_thumb.jpg"

    img.save(image_path, format="JPEG", quality=85, optimize=True)

    thumb = img.copy()
    thumb.thumbnail((THUMB_SIDE, THUMB_SIDE), Image.Resampling.LANCZOS)
    thumb.save(thumb_path, format="JPEG", quality=80, optimize=True)

    return image_path, thumb_path


def resolve_owned_file(stored_path: str) -> Path:
    """Resolve a stored path, refusing anything outside the upload directory."""
    path = Path(stored_path).resolve()
    root = UPLOAD_DIR.resolve()
    if root not in path.parents:
        raise HTTPException(status_code=404, detail="Fayl topilmadi")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fayl topilmadi")
    return path


def remove_files(*paths: str) -> None:
    for raw in paths:
        try:
            Path(raw).unlink(missing_ok=True)
        except OSError:
            pass
