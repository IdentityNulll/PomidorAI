/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Public origin of the API, with no trailing slash and no /api suffix.
   * Unset locally, where FastAPI serves this bundle from the same origin.
   */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
