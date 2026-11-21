"""Shared test fixtures: isolated database and upload directory per test."""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import db, images, session as sess
from app.main import app


@pytest.fixture(autouse=True)
def skip_model_warmup(monkeypatch):
    """The TestClient runs lifespan; do not let it preload the models."""
    monkeypatch.setattr("app.main.vision_models.warm", lambda: None)


STUB_RESULT = {
    "plant": {
        "id": "tomato",
        "commonName": "Pomidor",
        "scientificName": "Solanum lycopersicum",
        "confidence": 0.91,
    },
    "health": {
        "predictions": [
            {"label": "Sog'lom", "confidence": 0.78},
            {"label": "Fitoftoroz (kech kuyish)", "confidence": 0.14},
        ]
    },
    "info": {
        "description": "Pomidor haqida qisqa ma'lumot.",
        "howItGrows": "Ko'chatdan o'stiriladi.",
        "water": "Haftada 2-3 marta.",
        "sunlight": "To'liq quyosh.",
        "soil": "Yengil tuproq.",
        "season": "Mart - Sentabr",
        "commonDiseases": ["Fitoftoroz"],
        "careTips": ["Pastki barglarni olib tashlang."],
    },
}


@pytest.fixture(autouse=True)
def stub_analyzer(monkeypatch):
    """Keep API tests off the real models.

    These tests cover routing, sessions, storage and permissions - loading a
    gigabyte of weights to assert on them would be slow and would make the
    assertions depend on model output. The real models are covered in
    test_analyzer.py.
    """
    monkeypatch.setattr("app.main.analyze", lambda _path, _corrections=None: STUB_RESULT)


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    """Redirect uploads to a temp directory."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(images, "UPLOAD_DIR", upload_dir)
    return upload_dir


@pytest.fixture
def client(tmp_path, uploads):
    """A TestClient backed by a throwaway SQLite file."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db.Base.metadata.create_all(bind=engine)

    def override_get_db():
        database = TestingSession()
        try:
            yield database
        finally:
            database.close()

    app.dependency_overrides[db.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_image(color: str = "green", size: tuple[int, int] = (120, 90)) -> BytesIO:
    """A small valid JPEG."""
    buffer = BytesIO()
    Image.new("RGB", size, color=color).save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer


def session_cookie(session_id: str) -> dict[str, str]:
    """A correctly signed session cookie for the given id."""
    return {sess.COOKIE_NAME: sess.sign(session_id)}


def post_scan(client: TestClient, session_id: str | None = None):
    """Upload one image, optionally as a specific session."""
    cookies = session_cookie(session_id) if session_id else {}
    return client.post(
        "/api/analyze",
        files={"image": ("photo.jpg", make_image(), "image/jpeg")},
        cookies=cookies,
    )
