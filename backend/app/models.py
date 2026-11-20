"""Pydantic models mirroring frontend/src/types.ts."""

from datetime import datetime

from pydantic import BaseModel


class PlantResult(BaseModel):
    id: str
    commonName: str
    scientificName: str
    confidence: float


class HealthPrediction(BaseModel):
    label: str
    confidence: float


class HealthResult(BaseModel):
    predictions: list[HealthPrediction]


class PlantInfo(BaseModel):
    description: str
    howItGrows: str
    water: str
    sunlight: str
    soil: str
    season: str
    commonDiseases: list[str]
    careTips: list[str]


class Scan(BaseModel):
    id: str
    plant: PlantResult
    health: HealthResult
    createdAt: datetime


class ScanDetail(Scan):
    info: PlantInfo


class ScanListResponse(BaseModel):
    scans: list[Scan]
    cursor: str | None = None


class HealthResponse(BaseModel):
    status: str
