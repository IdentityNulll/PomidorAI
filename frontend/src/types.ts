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

/** What the app read the photo as: hosil / o'simlik / barg, or '' if unknown. */
export type PhotoView = string;

export interface ScanDetail extends Scan {
  info: PlantInfo;
  /** Empty for scans saved before the view classifier existed. */
  view?: PhotoView;
}

export interface ScanListResponse {
  scans: Scan[];
  cursor: string | null;
}
