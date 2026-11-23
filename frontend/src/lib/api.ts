import { uz } from '../i18n/uz';
import type { PlantOption, ScanDetail, ScanListResponse } from '../types';

/**
 * Same-origin by default: FastAPI serves this bundle itself in the normal
 * deployment. The Netlify build sets VITE_API_BASE to the public URL of a
 * tunnel pointing at the machine running the models.
 */
const API_BASE = `${import.meta.env.VITE_API_BASE ?? ''}/api`;

/**
 * The session cookie is httpOnly, so it only travels if every request opts
 * in. Same-origin requests do this by default; cross-origin ones do not,
 * and without it every scan would land in a brand new session.
 */
const CREDENTIALS: RequestInit = { credentials: 'include' };

async function failure(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body && typeof body.detail === 'string' ? body.detail : fallback;
  return new Error(detail);
}

export async function analyzeImage(image: Blob): Promise<ScanDetail> {
  const form = new FormData();
  form.append('image', image, 'scan.jpg');

  const response = await fetch(`${API_BASE}/analyze`, {
    ...CREDENTIALS,
    method: 'POST', body: form });
  if (!response.ok) throw await failure(response, uz.errorAnalysisFailed);
  return response.json();
}

export async function getScans(
  cursor?: string | null,
  limit = 20,
): Promise<ScanListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set('cursor', cursor);

  const response = await fetch(`${API_BASE}/scans?${params}`, CREDENTIALS);
  if (!response.ok) throw await failure(response, uz.errorHistoryFailed);
  return response.json();
}

export async function getScan(scanId: string): Promise<ScanDetail> {
  const response = await fetch(`${API_BASE}/scans/${scanId}`, CREDENTIALS);
  if (!response.ok) throw await failure(response, uz.errorNotFound);
  return response.json();
}

export function scanThumbUrl(scanId: string): string {
  return `${API_BASE}/scans/${scanId}/thumb`;
}

export function scanImageUrl(scanId: string): string {
  return `${API_BASE}/scans/${scanId}/image`;
}

export async function getPlants(): Promise<PlantOption[]> {
  const response = await fetch(`${API_BASE}/plants`, CREDENTIALS);
  if (!response.ok) throw await failure(response, uz.errorHistoryFailed);
  return response.json();
}

export async function correctScan(scanId: string, plantId: string): Promise<ScanDetail> {
  const response = await fetch(`${API_BASE}/scans/${scanId}/correct`, {
    ...CREDENTIALS,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plantId }),
  });
  if (!response.ok) throw await failure(response, uz.errorCorrectFailed);
  return response.json();
}

export async function deleteScan(scanId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/scans/${scanId}`, {
    ...CREDENTIALS,
    method: 'DELETE' });
  if (!response.ok) throw await failure(response, uz.errorDeleteFailed);
}

export async function deleteAllScans(): Promise<void> {
  const response = await fetch(`${API_BASE}/scans`, {
    ...CREDENTIALS,
    method: 'DELETE' });
  if (!response.ok) throw await failure(response, uz.errorDeleteFailed);
}
