export interface Plant {
  id: string;
  commonName: string;
  scientificName: string;
  confidence: number;
}

export interface HealthPrediction {
  label: string;
  confidence: number;
}

export interface Health {
  predictions: HealthPrediction[];
}

export interface PlantInfo {
  description: string;
  howItGrows: string;
  water: string;
  sunlight: string;
  soil: string;
  season: string;
  commonDiseases: string[];
  careTips: string[];
}

export interface Scan {
  id: string;
  plant: Plant;
  health: Health;
  createdAt: string;
}

export interface ScanDetail extends Scan {
  info: PlantInfo;
}

export interface ScanListResponse {
  scans: Scan[];
  cursor: string | null;
}
