/**
 * Where the API lives.
 *
 * Three sources, most specific first:
 *
 *   1. localStorage - set by the user in the "Haqida" tab. This exists
 *      because the usual way to run this split setup is a Cloudflare quick
 *      tunnel, whose URL changes every time it restarts. Baking the URL in
 *      at build time would mean a redeploy after every restart.
 *   2. VITE_API_BASE - baked in at build time, a sensible default for a
 *      stable backend address.
 *   3. Empty - same origin, which is the normal deployment where FastAPI
 *      serves this bundle itself.
 */

const STORAGE_KEY = 'pomidorai.backend';

function clean(value: string): string {
  // Tolerate a pasted trailing slash or a pasted "/api" suffix.
  return value.trim().replace(/\/+$/, '').replace(/\/api$/, '');
}

export function getBackendUrl(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return clean(stored);
  } catch {
    // Private mode or storage disabled; fall through to the build-time value.
  }
  return clean(import.meta.env.VITE_API_BASE ?? '');
}

export function setBackendUrl(value: string): void {
  const cleaned = clean(value);
  try {
    if (cleaned) localStorage.setItem(STORAGE_KEY, cleaned);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing useful to do; the caller still sees the value it set.
  }
}

/** True when the API is on another origin, so the UI can explain itself. */
export function isRemoteBackend(): boolean {
  return getBackendUrl() !== '';
}
