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
    # The disease library entry, so the UI can explain the diagnosis rather
    # than just naming it. Defaulted because scans saved before the library
    # existed are replayed through this same model.
    slug: str = ""
    alsoCalled: str = ""
    whatIsIt: str = ""
    signs: list[str] = []
    whyItHappens: str = ""
    whatToDo: list[str] = []
    prevent: list[str] = []


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
    # What the analyzer read the photo as: hosil / o'simlik / barg. Empty for
    # scans stored before the view classifier existed.
    view: str = ""


class PlantOption(BaseModel):
    id: str
    commonName: str
    scientificName: str


class CorrectionRequest(BaseModel):
    # A plants.json id the user says is actually right.
    plantId: str


class ScanListResponse(BaseModel):
    scans: list[Scan]
    cursor: str | None = None


class HealthResponse(BaseModel):
    status: str
