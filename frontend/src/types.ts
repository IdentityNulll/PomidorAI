export interface Plant {
  id: string;
  commonName: string;
  scientificName: string;
  confidence: number;
}

export interface HealthPrediction {
  label: string;
  confidence: number;
  /** Key into the backend's disease library. */
  slug?: string;
  alsoCalled?: string;
  whatIsIt?: string;
  /** How to recognise it on the plant. */
  signs?: string[];
  whyItHappens?: string;
  /** What to do now. */
  whatToDo?: string[];
  /** How to avoid it next season. */
  prevent?: string[];
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

/** A crop the user can pick when correcting a wrong identification. */
export interface PlantOption {
  id: string;
  commonName: string;
  scientificName: string;
}
