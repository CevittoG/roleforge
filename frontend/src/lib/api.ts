import type {
  ApplicationSummary,
  DownloadKey,
  DuplicateResponse,
  GenerateRequest,
  GenerateResponse,
} from './types';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class DuplicateError extends Error {
  constructor(public readonly existing: ApplicationSummary) {
    super('duplicate application');
    this.name = 'DuplicateError';
  }
}

async function fetchJson<T>(input: string, init?: RequestInit): Promise<T> {
  const res = await fetch(input, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = `request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // Non-JSON error body, fall through with default message.
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export async function generate(
  req: GenerateRequest,
  signal?: AbortSignal,
): Promise<ApplicationSummary> {
  const res = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(req),
    signal,
  });
  if (res.status === 409) {
    const body = (await res.json()) as DuplicateResponse;
    throw new DuplicateError(body.existing);
  }
  if (!res.ok) {
    let detail = `generate failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === 'string') detail = body.detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }
  const body = (await res.json()) as GenerateResponse;
  return body.application;
}

export function listApplications(signal?: AbortSignal): Promise<ApplicationSummary[]> {
  return fetchJson<ApplicationSummary[]>('/api/applications', { signal });
}

export function downloadUrl(folderId: string, file: DownloadKey): string {
  const params = new URLSearchParams({ folder_id: folderId, file });
  return `/api/download?${params.toString()}`;
}

export async function warmPing(signal?: AbortSignal): Promise<void> {
  try {
    await fetch('/api/healthz', { signal, cache: 'no-store' });
  } catch {
    // Warm ping is best-effort; surface nothing to the user.
  }
}
