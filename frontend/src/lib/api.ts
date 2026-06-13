import type {
  AppConfig,
  ApplicationStatus,
  ApplicationSummary,
  DownloadKey,
  GenerateRequest,
  GenerateResponse,
  JobResponse,
  LlmProvider,
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
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function startGenerate(
  req: GenerateRequest,
  signal?: AbortSignal,
): Promise<GenerateResponse> {
  return fetchJson<GenerateResponse>('/api/generate', {
    method: 'POST',
    body: JSON.stringify(req),
    signal,
  });
}

export async function getJob(jobId: string, signal?: AbortSignal): Promise<JobResponse> {
  return fetchJson<JobResponse>(`/api/jobs/${encodeURIComponent(jobId)}`, { signal });
}

export function listApplications(signal?: AbortSignal): Promise<ApplicationSummary[]> {
  return fetchJson<ApplicationSummary[]>('/api/applications', { signal });
}

export function getConfig(signal?: AbortSignal): Promise<AppConfig> {
  return fetchJson<AppConfig>('/api/config', { signal });
}

export async function updateApplicationStatus(
  folderId: string,
  status: ApplicationStatus,
  signal?: AbortSignal,
): Promise<void> {
  await fetchJson<void>(
    `/api/applications/${encodeURIComponent(folderId)}/status`,
    {
      method: 'PATCH',
      body: JSON.stringify({ status }),
      signal,
    },
  );
}

export async function generateInterviewPrep(
  folderId: string,
  provider?: LlmProvider,
  signal?: AbortSignal,
): Promise<void> {
  await fetchJson<void>(
    `/api/applications/${encodeURIComponent(folderId)}/interview-prep`,
    { method: 'POST', body: JSON.stringify({ provider: provider ?? null }), signal },
  );
}

export function downloadUrl(folderId: string, file: DownloadKey): string {
  const params = new URLSearchParams({ folder_id: folderId, file });
  return `/api/download?${params.toString()}`;
}

export async function warmPing(signal?: AbortSignal): Promise<void> {
  try {
    // /healthz lives outside the /api router so it works without a CF Access
    // JWT or origin secret — also what Render's platform health check uses.
    await fetch('/healthz', { signal, cache: 'no-store' });
  } catch {
    // Warm ping is best-effort; surface nothing to the user.
  }
}
