"""Database engine, model and session helpers."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, LargeBinary, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = Path(__file__).parent.parent / "data" / "pomidorai.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def new_id() -> str:
    return uuid.uuid4().hex


class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=new_id)
    session_id = Column(String, index=True, nullable=False)
    image_path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=False)
    result = Column(Text, nullable=False)
    created_at = Column(
        DateTime,
        index=True,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )


class Correction(Base):
    """A user saying "that is not what it is - it is this".

    The CLIP embedding of the photo is stored alongside the label, so the
    analyzer can recognise a similar photo later without any retraining.
    512 float32 values, about 2 KB per correction.

    Corrections are deliberately NOT scoped to a session: the point is that
    the app gets better for everyone as it is used. The stored vector is not
    reversible into the photo.
    """

    __tablename__ = "corrections"

    id = Column(String, primary_key=True, default=new_id)
    plant_id = Column(String, index=True, nullable=False)
    embedding = Column(LargeBinary, nullable=False)
    # What the model had said, kept so mistakes can be reviewed later.
    predicted_id = Column(String, nullable=True)
    created_at = Column(
        DateTime,
        index=True,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
