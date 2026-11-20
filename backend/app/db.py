"""Database engine, model and session helpers."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, String, Text, create_engine
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


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
