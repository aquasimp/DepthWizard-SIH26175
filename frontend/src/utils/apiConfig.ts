/**
 * apiConfig.ts
 * Manages dynamic API Base URL resolution and health checks for DepthWizard.
 * Supports configurable remote backends (Render, Railway, EC2, Ngrok, localhost)
 * or standalone in-browser operation on Vercel.
 */

const STORAGE_KEY = 'depthwizard_api_base';

export function getApiBase(): string {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved !== null) {
      return saved.trim().replace(/\/+$/, '');
    }
  }

  const envUrl =
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL ||
    (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');

  return String(envUrl).trim().replace(/\/+$/, '');
}

export function setApiBase(url: string): void {
  if (typeof window !== 'undefined') {
    const cleanUrl = url.trim().replace(/\/+$/, '');
    if (cleanUrl) {
      localStorage.setItem(STORAGE_KEY, cleanUrl);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
}

export interface BackendHealthResponse {
  status: string;
  model_version?: string;
  model_name?: string;
  device?: string;
  cuda_available?: boolean;
  environment?: {
    cuda_available?: boolean;
    device_name?: string;
    python_version?: string;
  };
  active_checkpoint?: string;
  [key: string]: any;
}

export async function checkBackendHealth(targetBase?: string): Promise<{
  ok: boolean;
  data: BackendHealthResponse | null;
  error?: string;
}> {
  const base = targetBase !== undefined ? targetBase.trim().replace(/\/+$/, '') : getApiBase();
  const url = base ? `${base}/api/health` : '/api/health';

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3500);

    const res = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      return { ok: false, data: null, error: `HTTP ${res.status}: ${res.statusText}` };
    }

    const data = await res.json();
    return { ok: true, data };
  } catch (err: any) {
    const isAbort = err?.name === 'AbortError';
    return {
      ok: false,
      data: null,
      error: isAbort ? 'Connection timed out (3.5s)' : (err.message || 'Network error'),
    };
  }
}
